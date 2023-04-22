import sqlite3

con = sqlite3.connect('templates/db/users.db')
cur = con.cursor()
query = "SELECT password FROM users WHERE login = ?"
password = cur.execute(query, ('AlVoro',)).fetchone()[0]
print(password)

con.close()
