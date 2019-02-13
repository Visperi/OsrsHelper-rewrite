import MySQLdb


def connect(password):
    connection = MySQLdb.connect(host="localhost", user="Admin", password=password, database="osrshelper")
    return connection
