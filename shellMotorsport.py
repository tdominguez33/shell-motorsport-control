import asyncio
from bleak import BleakScanner, BleakClient
from threading import Thread
from configparser import ConfigParser
from time import sleep

# Leemos el archivo de configuración
config = ConfigParser()
config.read('config.ini')

UUID_CARACTERISTICA = "d44bc439-abfd-45a2-b575-925416129600"    # UUID de la caracteristica donde se envian los valores, igual para todos los autos

### Configuraciones ###
CONEXION_ESPECIFICA = int(config['CONEXION']['conexion_especifica'])
NOMBRE_AUTO         = config['CONEXION']['nombre']
INTENTOS_RECONEXION = int(config['CONEXION']['intentos_reconexion'])
DEADZONE_GATILLO    = int(config['MOVIMIENTO']['deadzone_gatillo'])
DEADZONE_ANALOGICO  = int(config['MOVIMIENTO']['deadzone_analogico'])

# Códigos para el auto
NEUTRAL         = config['CODIGOS']['NEUTRAL']
ADELANTE        = config['CODIGOS']['adelante']
ADELANTE_IZQ    = config['CODIGOS']['adelante_izq']
ADELANTE_DER    = config['CODIGOS']['adelante_der']
ATRAS           = config['CODIGOS']['atras']
ATRAS_IZQ       = config['CODIGOS']['atras_izq']
ATRAS_DER       = config['CODIGOS']['atras_der']
IZQUIERDA       = config['CODIGOS']['izquierda']
DERECHA         = config['CODIGOS']['derecha']

TURBO_ADELANTE        = config['CODIGOS']['turbo_adelante']
TURBO_ADELANTE_IZQ    = config['CODIGOS']['turbo_adelante_izq']
TURBO_ADELANTE_DER    = config['CODIGOS']['turbo_adelante_der']
TURBO_ATRAS           = config['CODIGOS']['turbo_atras']
TURBO_ATRAS_IZQ       = config['CODIGOS']['turbo_atras_izq']
TURBO_ATRAS_DER       = config['CODIGOS']['turbo_atras_der']

salir = False

# En caso de que no se quiera elegir que control usar se toma el primero que aparezca disponible
def elegirControlPredeterminado():
    import inputs
    from sys import exit

    gamepads = inputs.devices.gamepads  # Obtenemos una lista de todos los gamepads disponibles
    
    if len(gamepads) == 0:
        print("No hay controles disponibles.")
        exit()
    else:
        gamepad = gamepads[0]   # Elegimos el primer control de la lista
    return gamepad


# Recibe la variable controlValores y determina que paquete se envia
def elegirPaquete(controlValores):
    # Leemos el control y determinamos que valor escribir

    if(controlValores['BTN_SOUTH'] == 1):
        turbo = True
    else:
        turbo = False

    # Gatillo Derecho - Avanzando
    if(controlValores['ABS_RZ'] > DEADZONE_GATILLO):
        # Doblando Derecha
        if(controlValores['ABS_X'] > DEADZONE_ANALOGICO):
            if turbo:
                return bytearray.fromhex(TURBO_ADELANTE_DER)
            else:
                return bytearray.fromhex(ADELANTE_DER)
        
        # Doblando Izquierda
        elif(controlValores['ABS_X'] < -DEADZONE_ANALOGICO):
            if turbo:
                return bytearray.fromhex(TURBO_ADELANTE_IZQ)
            else:
                return bytearray.fromhex(ADELANTE_IZQ)
        
        # Sin Doblar
        else:
            if turbo:
                return bytearray.fromhex(TURBO_ADELANTE)
            else:
                return bytearray.fromhex(ADELANTE)
    
    # Gatillo Izquierdo - Retrocediendo
    elif(controlValores['ABS_Z'] > DEADZONE_GATILLO):
        # Doblando Derecha
        if(controlValores['ABS_X'] > DEADZONE_ANALOGICO):
            if turbo:
                return bytearray.fromhex(TURBO_ATRAS_DER)
            else:
                return bytearray.fromhex(ATRAS_DER)
        
        # Doblando Izquierda
        elif(controlValores['ABS_X'] < -DEADZONE_ANALOGICO):
            if turbo:
                return bytearray.fromhex(TURBO_ATRAS_IZQ)
            else:
                return bytearray.fromhex(ATRAS_IZQ)
        
        # Sin Doblar
        else:
            if turbo:
                return bytearray.fromhex(TURBO_ATRAS)
            else:
                return bytearray.fromhex(ATRAS)
            
    # Ningún Gatillo Presionado - Sin Moverse
    else:
        # Doblando Derecha
        if(controlValores['ABS_X'] > DEADZONE_ANALOGICO):
            return bytearray.fromhex(DERECHA)
        
        # Doblando Izquierda
        elif(controlValores['ABS_X'] < -DEADZONE_ANALOGICO):
            return bytearray.fromhex(IZQUIERDA)
        
        # Sin Doblar
        else:
            return bytearray.fromhex(NEUTRAL)

# Actualiza la variable controlValores con los datos del control
def actualizarControl(control):
    global controlValores, salir
    
    # Obtenemos los eventos del control elegido
    while not salir:
        events = control.read()  
        for event in events:
            if (event.ev_type == 'Key') or (event.ev_type == 'Absolute'):  # Eventos de botones (Key) o joysticks y gatillos (Absolute)
                controlValores[event.code] = event.state
        
        if(controlValores['BTN_SELECT'] == 1 and controlValores['BTN_START'] == 1):
            salir = True


async def conexionAuto(hiloControl):
    global salir

    print("Buscando dispositivo...")
    intentos = 0
    conexionActiva = False

    while intentos <= INTENTOS_RECONEXION and not salir and not conexionActiva:

        # Escanear dispositivos disponibles
        devices = await BleakScanner.discover()

        nombreAuto = None
        direccionAuto = None
        for device in devices:
            print(f"Dispositivo encontrado: {device.name} ({device.address})")
            if (device.name == NOMBRE_AUTO) or (device.name != None and "QCAR-" in device.name and CONEXION_ESPECIFICA == 0):
                nombreAuto = device.name
                direccionAuto = device.address
                break

        if direccionAuto is None:
            print(f"Dispositivo no encontrado, reintentando {str(INTENTOS_RECONEXION - intentos)} veces más")
            intentos += 1
        else:
            conexionActiva = True

    # Conectar al dispositivo
    while intentos <= INTENTOS_RECONEXION and not salir and conexionActiva == 1:
        try:
            async with BleakClient(direccionAuto) as client:

                # Limpiamos toda la pantalla
                print('\033[2J', end="")
                # Movemos el cursor al inicio de la pantalla
                print('\033[H', end="")
                
                print(f"Conectado a {nombreAuto} ({direccionAuto})")

                # Comenzamos el hilo que lee los valores del control
                hiloControl.start()

                ultimoPaquete = None
                while conexionActiva and not salir:
                    # Leemos el control y decidimos que paquete se envia
                    valorEnviar = elegirPaquete(controlValores)
                    if ultimoPaquete != NEUTRAL:
                        try:
                            # Escribimos el valor en el auto
                            await client.write_gatt_char(UUID_CARACTERISTICA, valorEnviar)

                            # Borramos la linea actual
                            print('\033[0K', end="")
                            print(f"Escrito {valorEnviar}", end="\r")
                            ultimoPaquete = valorEnviar
                        except:
                            print("\nError en el envio del paquete, intentando reconectar")
                            conexionActiva = False
        except:
            print("Error en la reconexión, intentando " + str(INTENTOS_RECONEXION - intentos) + " veces más")
            intentos += 1

    # Si llegamos a este punto quiere decir que debemos salir del programa
    salir = True

control = elegirControlPredeterminado()

controlValores = {
    'BTN_SOUTH': 0, 'BTN_EAST': 0, 'BTN_WEST': 0, 'BTN_NORTH': 0,
    'BTN_TL': 0, 'BTN_TR': 0, 'BTN_START': 0, 'BTN_SELECT': 0,
    'ABS_X': 0, 'ABS_Y': 0, 'ABS_RX': 0, 'ABS_RY': 0,
    'ABS_Z': 0, 'ABS_RZ': 0, 'ABS_HAT0X': 0, 'ABS_HAT0Y': 0,
    'BTN_THUMBL': 0, 'BTN_THUMBR': 0
}   # Valores crudos obtenidos del control


hiloControl = Thread(target=actualizarControl, args=(control, ))
hiloBluetooth = Thread(target=asyncio.run, args=(conexionAuto(hiloControl), ))

hiloBluetooth.start()
hiloBluetooth.join()

print("\nBye Bye!")
sleep(2)