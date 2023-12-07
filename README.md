# disLi
Discord Library! An easy way for friends to share and swap books

Create a virtual library on your discord server, where each member can add books, checkout books, and return them
built using python, discord.py, mongodb, and googleBooks API

## add

```
--add <BOOK_NAME>
```

searches Google Books API, based on the given BOOK_NAME, and returns the top 3 results
then by reacting to the correct book, it gets added as an entry into the Library database, storing the person who added it as the owner



## library

```
--library
```

returns a list of the books stored in this Discord server, along with the number of available copies of each book

## checkout
```
--checkout <BOOK_NAME>
```

searches our database for a matching book, as well as partial matches, if there is more than 1 match, the user selects which one they want

## return
```
  --return
```
calling the command with no arguments will return your book if you have exactly 1 book checked out, or return a list of books you have checked out, and allow you to pick between them
```
  --return <BOOK_NAME>
```
looks for a book checked out my the user matching the title <BOOK_NAME>, if there multiple matches (partial matching), the user selects from the options given and types the corresponding number


