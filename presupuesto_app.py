from nicegui import ui
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color
from datetime import datetime
import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager

# Lista para almacenar los ítems de presupuesto
items = []
# Variable global para llevar el contador de presupuestos
PRESUPUESTO_COUNTER = 0
# Variable global para almacenar los productos de la base de datos
productos = []
# Definimos las dimensiones del logo como constantes al inicio del archivo
LOGO_WIDTH = 250
LOGO_HEIGHT = 100

# URL directa de la base de datos de Render
DATABASE_URL = "postgresql://presupuesto_db_user:eigRQ0n91eXV46PdDNiJ3VyA0ESGWzAK@dpg-csulfndds78s738naf3g-a.oregon-postgres.render.com/presupuesto_db"

@contextmanager
def get_db_connection():
    """Administrador de contexto para conexiones a la base de datos"""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    finally:
        if conn is not None:
            conn.close()

def init_database():
    """Inicializa la base de datos con la tabla necesaria y los datos específicos"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Crear tabla si no existe (solo cod y descripcion)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS materiales (
                    cod VARCHAR(50) PRIMARY KEY,
                    descripcion TEXT NOT NULL
                )
            """)
            
            # Insertar los datos específicos
            try:
                cur.execute("""
                    INSERT INTO materiales (cod, descripcion) VALUES
                    ('001', 'Color a elección'),
                    ('002', 'Instalación y Flete incluido')
                    ON CONFLICT (cod) DO UPDATE 
                    SET descripcion = EXCLUDED.descripcion
                """)
                conn.commit()
            except Exception as e:
                print(f"Error al insertar datos: {e}")

def cargar_productos():
    """Carga los productos desde la base de datos"""
    global productos
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('SELECT cod, descripcion FROM materiales')
                productos = [dict(row) for row in cur.fetchall()]
        return True
    except Exception as e:
        ui.notify(f'Error al cargar productos: {str(e)}', color='negative')
        return False

def actualizar_descripcion(e):
    """Actualiza el precio cuando se selecciona un producto"""
    selected_product = next((p for p in productos if p['descripcion'] == description_input.value), None)
    if selected_product:
        price_input.text = f'Precio Unitario: ${selected_product["precio"]:.2f}'

def add_background_image(canvas, doc):
    # Guardar el estado actual del canvas
    canvas.saveState()
    
    # Obtener dimensiones de la página
    width, height = letter
    
    # Cargar y dibujar la imagen de fondo
    canvas.drawImage('images/fondo.png',  # Asegúrate de que la imagen esté en esta ruta
                    0,           # x
                    0,           # y
                    width=width, # ancho completo de la página
                    height=height, # alto completo de la página
                    mask='auto',
                    preserveAspectRatio=False)  # Ajustar a página completa
    
    canvas.restoreState()

def generate_pdf():
    if not items:
        ui.notify('Agregue al menos un ítem al presupuesto', color='warning')
        return
        
    if not name_input.value:
        ui.notify('Ingrese el nombre del cliente', color='warning')
        return

    # Incrementar el contador de presupuestos
    global PRESUPUESTO_COUNTER
    PRESUPUESTO_COUNTER += 1

    # Crear nombre del archivo con fecha y hora
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Crear directorio 'presupuestos' si no existe
    if not os.path.exists('presupuestos'):
        os.makedirs('presupuestos')
    
    filename = os.path.join('presupuestos', f"presupuesto_{timestamp}.pdf")
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    # Crear el documento PDF con un canvas personalizado
    def custom_bg(canvas, doc):
        add_background_image(canvas, doc)

    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos personalizados
    styles = getSampleStyleSheet()
    
    # Estilo para el título principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=5,
        alignment=0  # Alineado a la izquierda
    )

    # Estilo para subtítulos
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=13,
        textColor=HexColor('#2d3748'),
        spaceAfter=10,
        alignment=0,
        leading=18  # Alineado a la izquierda
    )

    # Estilo para "CLIENTE"
    client_title_style = ParagraphStyle(
        'ClientTitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#4a5568'),
        spaceAfter=5,
        alignment=0  # Alineado a la izquierda
    )

    # Estilo para información del cliente
    client_info_style = ParagraphStyle(
        'ClientInfo',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#2d3748'),
        spaceAfter=20,
        alignment=0  # Alineado a la izquierda
    )

    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#2d3748'),
        spaceAfter=20,
        alignment=0  # Alineado a la izquierda
    )
    
    # Estilo para el número de presupuesto
    number_style = ParagraphStyle(
        'NumberStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#4a5568'),
        spaceAfter=5,
        alignment=1  # Alineado a la izquierda
    )
    
    # Estilo para la fecha
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#4a5568'),
        spaceAfter=20,
        alignment=1  # Alineado a la izquierda
    )

    # Crear tabla para el encabezado (título y logo)
    try:
        # Load the logo with maintained aspect ratio
        logo = Image('images/ep_logo.png')
        logo.keepAspectRatio = True
        
        # Calculate scaling to fit within a specific width while maintaining aspect ratio
        max_width_inches = 2  # Adjust this value to control maximum logo width
        scaling_factor = min(1, max_width_inches * inch / logo.imageWidth)
        
        logo.drawWidth = logo.imageWidth * scaling_factor
        logo.drawHeight = logo.imageHeight * scaling_factor

        # Crear tabla para el encabezado completo
        header_data = [
            [
                # Columna izquierda con título
                Paragraph("", title_style),
                # Columna derecha con logo
                logo
            ],
            [
                # Columna izquierda con información del cliente
                Table([
                    [Paragraph("<b>CLIENTE</b>", client_title_style)],
                    [Paragraph(f"Nombre: {name_input.value}", client_info_style)]
                ], colWidths=[3*inch]),
                # Columna derecha con número y fecha
                Table([
                    [Paragraph(f"<b>Presupuesto N°:</b> {PRESUPUESTO_COUNTER:04d}", number_style)],
                    [Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", date_style)]
                ], colWidths=[2*inch])
            ]
        ]
        
    except Exception as e:
        print(f"Error loading logo: {e}")
        # Versión sin logo pero manteniendo la estructura
        header_data = [
            [
                Paragraph("", title_style),
                ""
            ],
            [
                # Columna izquierda con información del cliente
                Table([
                    [Paragraph("CLIENTE", client_title_style)],
                    [Paragraph(f"Nombre: {name_input.value}", client_info_style)]
                ], colWidths=[3*inch]),
                # Columna derecha con número y fecha
                Table([
                    [Paragraph(f"Presupuesto N°: {PRESUPUESTO_COUNTER:04d}", number_style)],
                    [Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", date_style)]
                ], colWidths=[3*inch])
            ]
        ]

    header_table = Table(header_data, colWidths=[4.5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # Alinear logo a la derecha
        ('ALIGN', (1, 1), (1, 1), 'RIGHT'),  # Alinear información derecha
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alinear todo verticalmente arriba
        ('LEFTPADDING', (0, 0), (-1, -1), 0),  # Sin padding izquierdo
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # Sin padding derecho
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 20))
    
    # Tabla de items con estilo moderno
    table_data = [['Descripción', 'Cantidad', 'Precio Unitario', 'Total']]  # Encabezado de la tabla
    for item in items:
        table_data.append([
            item['descripcion'],
            f"{item['cantidad']:.2f}",
            f"${item['precio_unitario']:.2f}",
            f"${item['total']:.2f}"
        ])
    
    # Calcular subtotal de los ítems
    subtotal = sum(item['total'] for item in items)
    
    # Aplicar bonificación si está habilitada
    bonus_amount = 0
    if bonus_checkbox.value:
        bonus_amount = float(bonus_input.value or 0)

    # Aplicar descuento del 20% si está habilitado
    discount_amount = 0
    if discount_checkbox.value:
        discount_amount = subtotal * 0.20
    
    # Calcular IVA según corresponda
    if vat_checkbox.value:
        iva = subtotal * 0.21
        total = subtotal + iva - bonus_amount - discount_amount
    else:
        iva = 0
        total = subtotal - bonus_amount - discount_amount
    
    # Agregar filas para Subtotal, IVA y Total
    table_data.append([None, None, 'Subtotal:', f"${subtotal:.2f}"])  # Usar None en lugar de ''
    if vat_checkbox.value:
        table_data.append([None, None, 'IVA (21%):', f"${iva:.2f}"])
    if discount_checkbox.value:
        table_data.append([None, None, 'Descuento (20%):', f"${discount_amount:.2f}"])
    if bonus_checkbox.value:
        table_data.append([None, None, 'Bonificación:', f"${bonus_amount:.2f}"])
    table_data.append([None, None, 'Total:', f"${total:.2f}"])

    
    # Crear tabla con estilo moderno
    table = Table(table_data, colWidths=[4*inch, 1*inch, 1.25*inch, 1.25*inch])
    # Aplica estilo específico para el encabezado y las filas de datos
    table.setStyle(TableStyle([
    # Estilo del encabezado
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#000000')),  # Color azul para encabezado
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Texto blanco en el encabezado
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Alinear el texto del encabezado
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Negrita en encabezado
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),

        # Estilo del cuerpo de la tabla (datos)
        ('TEXTCOLOR', (0, 1), (-1, -1), HexColor('#2d3748')),  # Texto oscuro en los datos
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Centrar cantidad, precio unitario y total
        ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),  # Fuente normal
        ('FONTSIZE', (0, 1), (-1, -4), 10),  # Tamaño de fuente para los datos
        ('BOTTOMPADDING', (0, 1), (-1, -4), 7),  # Aumentar espacio vertical en filas de datos
        ('TOPPADDING', (0, 1), (-1, -4), 7),
        ('GRID', (0, 0), (-1, -4), 1, HexColor('#e2e8f0')),  # Cuadrícula para las filas de datos
        ('VALIGN', (0, 0), (-1, -4), 'MIDDLE'),  # Alineación vertical en el medio

        # Estilo para los totales
        ('ALIGN', (2, -3), (-1, -1), 'RIGHT'),  # Alinear texto de Subtotal, IVA y Total a la derecha
        ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),  # Negrita en totales
        ('FONTSIZE', (2, -3), (-1, -1), 10),  # Tamaño de fuente para los totales
        ('TEXTCOLOR', (2, -3), (-1, -1), HexColor('#2d3748')),  # Texto oscuro para totales
        ('BOTTOMPADDING', (0, -4), (-1, -1), 7),  # Aumentar espacio vertical entre filas
        ('TOPPADDING', (0, -4), (-1, -1), 7),  # Aumentar espacio vertical entre filas
        # Eliminar líneas para los totales
        ('LINEBELOW', (0, -4), (-1, -4), 1, HexColor('#e2e8f0')),  # Línea solo antes de los totales
        ('LINEBELOW', (0, -3), (-1, -1), 0, colors.white),  # Eliminar bordes de Subtotal, IVA y Total
    ]))

    elements.append(table)
    
    # Agregar nota al pie
    elements.append(Spacer(1, 30))
    footer_text = "Nota: el presupuesto tiene una validez de 7 días."
    elements.append(Paragraph(footer_text, normal_style))
    
    # Generar PDF
    doc.build(elements, onFirstPage=custom_bg, onLaterPages=custom_bg)
    
    # Notificar al usuario
    ui.notify(f'PDF generado como "presupuestos/presupuesto_{timestamp}.pdf"', 
              color='positive', 
              position='center', 
              close_button=True, 
              timeout=5000)

# Agregado de items usando base de datos
def add_item():
    try:
        # Validar que los campos no estén vacíos o sean None
        if not description_input.value or quantity_input.value is None or price_input.value is None:
            ui.notify('Por favor, complete todos los campos', color='negative')
            return

        # Crear un diccionario para el ítem
        item = {
            'descripcion': description_input.value,
            'cantidad': float(quantity_input.value),
            'precio_unitario': float(price_input.value),
            'total': float(quantity_input.value) * float(price_input.value)
        }
        
        # Agregar el ítem a la lista
        items.append(item)
        
        # Actualizar la tabla
        items_table.rows = items
        
        # Limpiar los campos de entrada
        description_input.value = ''
        quantity_input.value = None
        price_input.value = None
        
        # Actualizar el total
        update_total()
        
        ui.notify('Ítem agregado correctamente', color='positive')
        
    except ValueError:
        ui.notify('Por favor, ingrese valores válidos', color='negative')

def clear_all():
    if items:
        items.clear()
        items_table.rows = []
        update_total()
        ui.notify('Todos los ítems han sido eliminados', color='info')
    else:
        ui.notify('No hay ítems para eliminar', color='warning')

def clear_user_data():
    # Limpiar todos los campos de usuario
    name_input.value = ''
    vat_checkbox.value = False
    ui.notify('Datos del cliente eliminados', color='info')

def on_bonus_change(e):
    # Habilitar/deshabilitar campo de bonificación según el estado de la casilla
    bonus_input.enabled = bonus_checkbox.value
    # Actualizar cálculo de total
    update_total()

def on_discount_change(e):
    # Actualizar cálculo de total
    update_total()

def update_total():
    # Calcular subtotal sumando todos los ítems
    total = sum(item['total'] for item in items)
    
    # Aplicar bonificación si está habilitada
    if bonus_checkbox.value:
        # Obtener monto de bonificación (0 si está vacío)
        bonus_amount = float(bonus_input.value or 0)
        # Restar bonificación del total
        total -= bonus_amount

    # Aplicar descuento del 20% si está habilitado
    if discount_checkbox.value:
        # Restar descuento del 20%
        total *= 0.8
    
    # Actualizar etiqueta de total sin IVA
    total_label.text = f'Total sin IVA: ${total:.2f}'
    
    # Actualizar total con IVA si está habilitado
    if vat_checkbox.value:
        total_with_vat_label.text = f'Total con IVA (21%): ${total * 1.21:.2f}'
    else:
        total_with_vat_label.text = ''

def on_vat_change(e):
    update_total()

# Interfaz de usuario
with ui.card().classes('max-w-3xl mx-auto p-4 m-4'):
    # Cargar productos al inicio
    if not cargar_productos():
        ui.label('Error al cargar productos de la base de datos').classes('text-red-500')
    
    # Encabezado con logo y título
    with ui.row().classes('w-full items-center justify-between mb-4'):
        ui.label('Generador de Presupuestos').classes('text-2xl font-bold')
        ui.image('images/ep_logo.png').style(f'height: {LOGO_HEIGHT}px; width: {LOGO_WIDTH}px; margin-left: auto; display: block; margin-right: 0;')

    # Sección de datos del cliente
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.column().classes('flex-1'):
            name_input = ui.input('Nombre del cliente').classes('w-full')
        with ui.column().classes('flex-1'):
            vat_checkbox = ui.checkbox('Incluir IVA (21%)', on_change=on_vat_change)
    
    # Botón para limpiar datos del usuario
    with ui.row().classes('w-full justify-end mb-4'):
        ui.button('Limpiar Datos del Cliente', on_click=clear_user_data).classes('bg-yellow-500 text-white')
    
    # Línea separadora visual
    ui.element('span').classes('block w-full border-t border-gray-200 my-4')
    
    # Sección de ingreso de ítems
    with ui.row().classes('w-full gap-4'):
        # Uso de select para la descripción
        description_input = ui.select(
            label='Producto', 
            options=[p['descripcion'] for p in productos],
            new_value_mode='add-unique'  # Allows adding new values
        ).classes('flex-1')

        quantity_input = ui.number('Cantidad', min=0, format='%.2f').classes('w-32')
        price_input = ui.number('Precio Unitario', min=None, format='%.2f').classes('w-32')
        ui.button('Agregar Ítem', on_click=add_item).classes('bg-blue-500 text-white')

        # Casilla para habilitar/deshabilitar bonificación
        bonus_checkbox = ui.checkbox('Aplicar Bonificación', on_change=on_bonus_change)
        # Campo de entrada para el monto de bonificación
        bonus_input = ui.number('Monto de Bonificación', min=0, format='%.2f').classes('w-32')
        bonus_input.enabled = False  # Inicialmente deshabilitado

        # Casilla para habilitar/deshabilitar descuento
        discount_checkbox = ui.checkbox('Aplicar Descuento (20%)', on_change=on_discount_change)

    # Tabla de ítems
    columns = [
        {'name': 'descripcion', 'label': 'Descripción', 'field': 'descripcion', 'align': 'left'},
        {'name': 'cantidad', 'label': 'Cantidad', 'field': 'cantidad', 'align': 'right'},
        {'name': 'precio_unitario', 'label': 'Precio Unitario', 'field': 'precio_unitario', 'align': 'right'},
        {'name': 'total', 'label': 'Total', 'field': 'total', 'align': 'right'}
    ]
    
    items_table = ui.table(
        columns=columns,
        rows=[],
        row_key='descripcion',
        pagination={'no-data-label': 'No hay datos', 'rows-per-page-label': 'Filas por página'}
    ).classes('w-full mt-4')

    # Botones de acción
    with ui.row().classes('w-full gap-4 mt-4'):
        ui.button('Generar PDF', on_click=generate_pdf).classes('bg-green-500 text-white')
        ui.button('Limpiar Todo', on_click=clear_all).classes('bg-red-500 text-white')

    # Sección de totales
    with ui.row().classes('w-full mt-4 justify-end gap-4'):
        total_label = ui.label('Total sin IVA: $0.00').classes('text-lg')
        total_with_vat_label = ui.label('').classes('text-lg font-bold')

# Inicializar la base de datos al inicio
init_database()

# Crear la aplicación
app = ui.run(
    port=int(os.environ.get('PORT', 8080)),
    host='0.0.0.0',
    reload=False,  # Deshabilitar el reload automático en producción
    show=False    # No abrir automáticamente el navegador
)

# Solo ejecutar el servidor si este archivo es el principal
if __name__ in {"__main__", "__mp_main__"}:
    app.run()
