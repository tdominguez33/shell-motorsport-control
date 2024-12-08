import asyncio
from bleak          import BleakScanner, BleakClient
from threading      import Thread
from configparser   import ConfigParser
from Crypto.Cipher  import AES
from time           import sleep

# Leemos el archivo de configuración
config = ConfigParser()
config.read('config.ini')

### Configuraciones ###
CONEXION_ESPECIFICA = int(config['CONEXION']['conexion_especifica'])
NOMBRE_AUTO         = config['CONEXION']['nombre']
INTENTOS_RECONEXION = int(config['CONEXION']['intentos_reconexion'])
DEADZONE_GATILLO    = int(config['MOVIMIENTO']['deadzone_gatillo'])
DEADZONE_ANALOGICO  = int(config['MOVIMIENTO']['deadzone_analogico'])

# Parámetros necesarios para la comunicación con el auto
KEY_AES         = config['PAQUETES']['key']
UUID_COMANDOS   = config['PAQUETES']['uuid_comandos']
UUID_BATERIA    = config['PAQUETES']['uuid_bateria']

# Variables Globales
salir = False
lucesEncendidas = False
bateria = "Obteniendo ..."  # Placeholder, se tiene que enviar un paquete para recibir el valor de la bateria

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
    global lucesEncendidas

    # Creamos un paquete de 16 bytes con todos los bytes en cero
    paquete = bytearray(16)

    # Añadimos los bytes de control
    paquete[1] = 0x43   # C
    paquete[2] = 0x54   # T
    paquete[3] = 0x4C   # L

    if(controlValores['BTN_SOUTH'] == 1):
        paquete[9] = 0x64   # Velocidad Turbo
    else:
        paquete[9] = 0x50   # Velocidad Normal

    if(controlValores['ABS_HAT0Y'] == -1):
        lucesEncendidas = True
    elif(controlValores['ABS_HAT0Y'] == 1):
        lucesEncendidas = False

    if lucesEncendidas:
        paquete[8] = 0x00   # Luces Encendidas
    else:
        paquete[8] = 0x01   # Luces No Encendidas

    # Gatillo Derecho - Avanzando
    if(controlValores['ABS_RZ'] > DEADZONE_GATILLO):
        paquete[4] = 0x01
    
    # Gatillo Izquierdo - Retrocediendo
    elif(controlValores['ABS_Z'] > DEADZONE_GATILLO):
        paquete[5] = 0x01
    
    # Doblando Izquierda
    if(controlValores['ABS_X'] < -DEADZONE_ANALOGICO):
        paquete[6] = 0x01
    
    # Doblando Derecha
    elif(controlValores['ABS_X'] > DEADZONE_ANALOGICO):
        paquete[7] = 0x01
    
    return paquete

# Encripta los paquetes con AES de 128 bits en modo ECB
def encriptarPaquete(paquete, key):
    key = bytes.fromhex(key)

    cipher = AES.new(key, AES.MODE_ECB)
    
    codigoEncriptado = bytearray()

    for byte in cipher.encrypt(paquete):
        codigoEncriptado.append(byte)

    return codigoEncriptado

# Desencripta los paquetes con AES de 128 bits en modo ECB
def desencriptarPaquete(paquete, key):
    key = bytes.fromhex(key)

    cipher = AES.new(key, AES.MODE_ECB)

    codigoDesencriptado = bytearray()

    for byte in cipher.decrypt(paquete):
        codigoDesencriptado.append(byte)

    return codigoDesencriptado

# Recibe un paquete y verifica si es un paquete que necesita ser reenviado constantemente para generar efecto
def necesitaReenvio(paquete):
    # Caso especial primer paquete
    if paquete == None:
        return True
    
    # Verificamos si estamos indicando avanzar o girar
    return (paquete[4] == 0x01) or (paquete[5] == 0x01) or (paquete[6] == 0x01) or (paquete[7] == 0x01)

# Función que se llama cuando la caracteristica a la que nos suscribimos envia un paquete
def guardarBateria(sender, respuesta):
    global bateria, bateriaByteArray, bateriaByte

    bateriaByteArray = desencriptarPaquete(respuesta, KEY_AES)
    
    # El valor crudo es el porcentaje de bateria, ya está encodeado en decimal
    bateria = str(bateriaByteArray[4]) + " %"

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

# Lee la variable actualizada por el otro hilo y envia los comandos al auto
async def conexionAuto(hiloControl):
    global salir, bateria

    print("Buscando auto...")

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

                # Nos suscribimos a la caracteristica que informa el porcentaje de bateria
                await client.start_notify(UUID_BATERIA, guardarBateria)

                # Comenzamos el hilo que lee los valores del control
                hiloControl.start()

                ultimoPaquete = None
                while conexionActiva and not salir:
                    # Leemos el control y decidimos que paquete se envia
                    paqueteDesencriptado = elegirPaquete(controlValores)

                    # Encriptamos el paquete
                    paqueteEncriptado = encriptarPaquete(paqueteDesencriptado, KEY_AES)
                    
                    # Solo enviamos el paquete si va a generar un cambio en el auto
                    if (not necesitaReenvio(ultimoPaquete)) and (paqueteDesencriptado == ultimoPaquete):
                        pass
                    else:
                        try:
                            # Escribimos el valor en el auto
                            await client.write_gatt_char(UUID_COMANDOS, paqueteEncriptado)

                            # Borramos hasta el final de la pantalla
                            print('\033[0J', end="")

                            print(f"Bateria = {bateria}")
                            print(f"Escrito {paqueteDesencriptado}", end="\r")
                            
                            ultimoPaquete = paqueteDesencriptado

                            # Movemos una linea para arriba, dejamos listo para borrar en el siguiente ciclo
                            print('\033[1F', end="")

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

print("\n\nBye Bye!")
sleep(2)