import os
import discord
from discord.ext import commands
import requests
import pymongo
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
TOKEN = os.getenv('DISCORD_TOKEN')
API_URL = "https://www.googleapis.com/books/v1/volumes"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='--', intents=intents)

client = pymongo.MongoClient(
    MONGO_URI)
db = client["disLI"]
collection = db["library_books"]


def search_google_books(query_string):
    parameters = {'q': query_string}

    response = requests.get(API_URL, parameters)

    if response.status_code == 200:
        data = response.json()
        books = data.get('items', [])
        return books[:3]
    else:
        return None


@bot.command(name='return')
async def return_book(ctx, *args):
    # --return <BOOK_NAME>: returns the book specified
    # --return : if you only have one book, it returns it, if you have 2+, selection process
    # --return -a: return all books you have
    book_search = ' '.join(args)

    # gets a list of the book entries that this user has currently checked out
    users_books = list(collection.find({"server_id": str(ctx.guild.id), "checked_out": str(ctx.author.id)}))

    # no arguments, just [prefix]return
    # Case 1: The user has checked out exactly 1 book, then return that book
    # Case 2: The user has no books currently checked out
    # Case 3: The user has more than 1 book checked out
    if not book_search:
        # CASE 1
        if len(users_books) == 1:
            returning_book = users_books[0]

            collection.update_one(
                {"_id": returning_book["_id"]},
                {
                    "$set": {"checked_out": None},
                }
            )

            embed = discord.Embed(title='Book returned!',
                                  description=f'**{returning_book["book_name"]}**'
                                              f'\n**{returning_book["author"]}** '
                                              f'\n returned to <@{int(returning_book["owner"])}>',
                                  color=0xFF5733)
            if returning_book["thumbnail_url"]:
                embed.set_thumbnail(url=returning_book["thumbnail_url"])
            await ctx.send(embed=embed)
            return

        # CASE 2
        elif len(users_books) == 0:
            await ctx.send(f'You do not have any books to return')
            return

        # CASE 3
        else:
            formatted_book_names = '\n'.join([f'{i + 1}. **{book["book_name"]}** by {book["author"]}'
                                              for i, book in enumerate(users_books)])

            def check_choice(message):
                return message.author == ctx.author and message.content.isdigit() and 1 <= int(message.content) <= len(
                    users_books)

            embed = discord.Embed(title="Which Book would you like to return? "
                                        "Type the number of the book you want to return",
                                  description=f'{formatted_book_names}',
                                  color=0xFF5733)
            await ctx.send(embed=embed)

            try:
                selection_message = await bot.wait_for('message', timeout=30.0, check=check_choice)
                selected_index = int(selection_message.content) - 1
                returning_book = users_books[selected_index]
            except TimeoutError:
                await ctx.send('you took too long, please try again')
                return

            collection.update_one(
                {"_id": returning_book["_id"]},
                {
                    "$set": {"checked_out": None},
                }
            )
            embed = discord.Embed(title='Book returned!',
                                  description=f'**{returning_book["book_name"]}**'
                                              f'\n**{returning_book["author"]}** '
                                              f'\n returned to <@{int(returning_book["owner"])}>',
                                  color=0xFF5733)
            if returning_book["thumbnail_url"]:
                embed.set_thumbnail(url=returning_book["thumbnail_url"])
            await ctx.send(embed=embed)

    else:
        matches = [book["book_name"] for book in users_books if book_search.lower() in book["book_name"].lower()]


@bot.command(name='checkout')
async def checkout_book(ctx, *args):
    # concatenate the users search into 1 string
    book_search = ' '.join(args)

    # get all the book entries from this server
    server_books = collection.find({"server_id": str(ctx.guild.id)})

    # now get all the unique books that are in the current server
    # note: this is just a list strings, not the actual book entries
    unique_books = server_books.distinct("book_name")

    # list of matching or partially matching books from unique_books based on the user input
    matches = [book for book in unique_books if book_search.lower() in book.lower()]

    # If no books found matching the search
    if not matches:
        await ctx.send(f'No books found for {book_search}')
        return

    # Exactly 1 match, so it is selected by default
    if len(matches) == 1:
        selected_book = matches[0]

    # There are 2+ matching books, display them all to the user, and let them pick which one they intended
    else:
        matching_formatted = '\n'.join([f'{i + 1}. {book}' for i, book in enumerate(matches)])

        def check_choice(message):
            return message.author == ctx.author and message.content.isdigit() and 1 <= int(message.content) <= len(
                matches)

        embed = discord.Embed(title='Multiple matching books! Type the number of the book you want',
                              description=f'{matching_formatted}',
                              color=0xFF5733)
        await ctx.send(embed=embed)

        try:
            selection_message = await bot.wait_for('message', timeout=30.0, check=check_choice)
            selected_index = int(selection_message.content) - 1
            selected_book = matches[selected_index]
        except TimeoutError:
            await ctx.send('you took too long, please try again')
            return

    # now we have the title of the book that is in our database
    # need to see how many copies are free
    copies = list(collection.find({'book_name': selected_book, 'server_id': str(ctx.guild.id), 'checked_out': None}))

    # all the copies are already checked out
    if len(copies) == 0:
        await ctx.send(f'Sorry! There are no available copies at this time, check another time')
        return

    # there is only 1 available copy, so they do not have to pick the owner
    # checked_out field will be updated to this users id
    if len(copies) == 1:
        selected_copy = copies[0]

    # there is more than 1 person they can borrow from, so they choose
    else:
        owners_formatted = '\n'.join([f'{i + 1}. {ctx.guild.get_member(int(copy["owner"])).display_name} - '
                                      f'[@{ctx.guild.get_member(int(copy["owner"]))}]'
                                      for i, copy in enumerate(copies)])
        embed = discord.Embed(title='Multiple owners available! Type the number of the person you want to borrow from',
                              description=f'{owners_formatted}',
                              color=0xFF5733)
        await ctx.send(embed=embed)

        def check_choice(message):
            return message.author == ctx.author and message.content.isdigit() and 1 <= int(message.content) <= len(
                copies)

        try:
            selection_message = await bot.wait_for('message', timeout=30.0, check=check_choice)
            selected_index = int(selection_message.content) - 1
            selected_copy = copies[selected_index]
        except TimeoutError:
            await ctx.send('you took too long, please try again')
            return

    # set the checked_out field to the id of the user who picked it
    collection.update_one(
        {"_id": selected_copy["_id"]},
        {
            "$set": {"checked_out": str(ctx.author.id)},
        }
    )

    owner_id = selected_copy['owner']
    embed = discord.Embed(title='Checked Out!',
                          description=f'You have borrowed **{selected_copy["book_name"]}** by  '
                                      f'**{selected_copy["author"]}** from <@{int(owner_id)}>',
                          color=0x5865F2)
    if selected_copy["thumbnail_url"]:
        embed.set_thumbnail(url=selected_copy["thumbnail_url"])
    await ctx.send(embed=embed)


@bot.command(name='library')
async def view_library(ctx):
    # await ctx.send(ctx.guild.id)
    server_books = collection.find({"server_id": str(ctx.guild.id)})
    unique_books = server_books.distinct("book_name")
    if len(unique_books) == 0:
        embed = discord.Embed(title='Empty Library!',
                              description=f'There are no Books in this Library\nTry /add <BOOK_NAME> to get started',
                              color=0xFF5733)
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title=f"Library for {ctx.guild.name}", color=discord.Color.green())
    for book in unique_books:
        copies = list(collection.find({"server_id": str(ctx.guild.id), "book_name": book}))
        available_copies = list(collection.find({"server_id": str(ctx.guild.id),
                                                 "book_name": book, "checked_out": None}))

        title = book
        author = copies[0]['author']
        quantity = len(available_copies)

        embed.add_field(
            name=title,
            value=f"**Author:** {author}\n**Available Copies:** {quantity}",
            inline=False
        )

    await ctx.send(embed=embed)


# command for adding a book into the collection
# returns the top 3 search results and user selects by reacting
@bot.command(name='add')
async def add_book(ctx, *args):
    search = ' '.join(args)

    # the case when user puts empty query (just /add)
    if not search:
        await ctx.send(f'Please Type a book name:\n --add BOOK_NAME or --add ISBN')
        return

    # returns the top 3 query results based on what the user gave
    books = search_google_books(search)

    # 200 status is not returned by API, nothing found matching our search
    if not books:
        await ctx.send(f'No results found, Please try again')
        return

    embeds = []
    for i, book in enumerate(books):
        info = book['volumeInfo']
        title = info.get('title', 'Unknown Title')
        subtitle = info.get('subtitle', '')
        thumbnail = info.get('imageLinks', {}).get('smallThumbnail', None)

        if subtitle != '':
            subtitle += '\n'
        authors = info.get('authors', ['Unknown Author'])

        embed = discord.Embed(title=title,
                              description=subtitle + '\n' + ', '.join(authors),
                              color=0xFF5733)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        embeds.append(embed)

    msg = await ctx.send(embeds=embeds)

    for emoji in ['1️⃣', '2️⃣', '3️⃣']:
        await msg.add_reaction(emoji)

    def check_reaction(reaction, user):
        return user == ctx.author and reaction.message.id == msg.id and reaction.emoji in ['1️⃣', '2️⃣', '3️⃣']

    try:
        reaction, _ = await bot.wait_for('reaction_add', timeout=30.0, check=check_reaction)

        # Get the selected book index
        selected_index = {'1️⃣': 0, '2️⃣': 1, '3️⃣': 2}[reaction.emoji]
        selected_book = books[selected_index]['volumeInfo']
        authors = selected_book.get('authors', ['Unknown Author'])

        existing_entry = collection.find_one({
            "server_id": str(ctx.guild.id),
            "book_name": selected_book.get('title', 'Unknown Title'),
            "author": ', '.join(selected_book.get('authors', ['Unknown Author']))
        })

        book_name = selected_book.get('title', 'Unknown Title')

        book_data = {
            "server_id": str(ctx.guild.id),
            "book_name": selected_book.get('title', 'Unknown Title'),
            "author": ', '.join(selected_book.get('authors', ['Unknown Author'])),
            "thumbnail_url": selected_book.get('imageLinks', {}).get('thumbnail', None),
            "owner": str(ctx.author.id),
            "checked_out": None
        }
        collection.insert_one(book_data)

        confirm = discord.Embed(title='Added Book to Library!',
                                description=f'{book_name}' + '\n' + ', '.join(authors),
                                color=0xFF5733)
        thumbnail = selected_book.get('imageLinks', {}).get('smallThumbnail', None)
        if thumbnail:
            confirm.set_thumbnail(url=thumbnail)
        await ctx.send(embed=confirm)
    except TimeoutError:
        await ctx.send('You took too long to react. Please run the command again.')


bot.run(TOKEN)
