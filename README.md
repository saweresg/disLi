# disLi
Discord Library! An easy way for friends to share and swap books

Create a virtual library on your discord server, where each member can add books, checkout books, and return them
built using python, discord.py, mongodb, and googleBooks API

# comands
**add**

USAGE: --add <BOOK_NAME>

searches Google Books API, based on the given BOOK_NAME, and returns the top 3 results
then by reacting to the correct book, it gets added as an entry into the Library database, storing the person who added it as the owner



**library**

USAGE: --library

returns a list of the books stored in this Discord server, along with the number of available copies of each book

**checkout**
USAGE: --checkout <BOOK_NAME>

searches our database for a matching book, as well as partial matches, if there is more than 1 match, the user selects which one they want

**return**
USAGE:
  --return
  --return <BOOK_NAME>

calling the command with no arguments will return your book if you have exactly 1 book checked out, or return a list of books you have checked out, and allow you to pick between them


