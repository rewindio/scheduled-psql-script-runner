import psycopg2

def make_conn(host, db, user, password):
    conn = None

    try:
        conn = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db, user, host, password))
    except:
        print("ERROR: make_conn - unable to connect to the database")

    return conn


def fetch_data(conn, query):
    result = []
    print("Running query: {}".format(query))

    cursor = conn.cursor()
    cursor.execute(query)

    raw = cursor.fetchall()
    for line in raw:
        result.append(line)

    return result
    
def fetch_data_to_file(conn, query, output_filename):
    print("Running query: {}".format(query))

    cursor = conn.cursor()
    
    outputquery = "COPY ({0}) TO STDOUT WITH CSV HEADER".format(query)
    
    with open(output_filename, 'w') as f:
        cursor.copy_expert(outputquery, f)