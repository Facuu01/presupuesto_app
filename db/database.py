import sqlite3

conn = sqlite3.connect('materiales.db')
print("Opened database successfully")

c = conn.cursor()

# Crear la tabla 'materiales'
c.execute('''
    CREATE TABLE IF NOT EXISTS materiales(
        cod INTEGER PRIMARY KEY,
        descripcion TEXT
    )
''')

# Lista de materiales
lista_materiales = [
    (1, 'Color a elección'),
    (2, 'Instalación y flete incluido'),
]

# Usar executemany para insertar múltiples registros
c.executemany('INSERT INTO materiales (cod, descripcion) VALUES (?, ?)', lista_materiales)

# Guardar cambios y cerrar conexión
conn.commit()
conn.close()