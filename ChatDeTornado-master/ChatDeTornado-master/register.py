import sqlite3

connector = sqlite3.connect("userdata.db")

sql = "insert into users values('maeda', 'maeda')"

connector.execute(sql)

sql = "insert into users values('honda', 'honda')"

connector.execute(sql)

sql = "insert into users values('yasui', 'yasui')"

connector.execute(sql)

 

connector.commit()
connector.close()
