import argparse
import serial as rs
import time as ti
import random as RA
import urllib.request
import json


def Make_Data(nId):
    nEMA  = nId                      # Identificador de la UMA (1..5)
    nMP01 = RA.randint(5, 100)       # Material Particulado 1.0 um
    nMP25 = RA.randint(5, 100)       # Material Particulado 2.5 um
    nMP10 = RA.randint(5, 100)       # Material Particulado 10 um

    nHi03 = RA.randint(10, 10000)    # Histograma MP 0.3 um
    nHi05 = RA.randint(10, 10000)    # Histograma MP 0.5 um
    nHi01 = RA.randint(10, 10000)    # Histograma MP 1.0 um
    nHi25 = RA.randint(10, 10000)    # Histograma MP 2.5 um
    nHi50 = RA.randint(10, 10000)    # Histograma MP 5.0 um
    nHi10 = RA.randint(10, 10000)    # Histograma MP 10 um

    nTE   = RA.randint(5, 30)        # Temperatura Celsius
    nHR   = RA.randint(20, 70)       # Humedad Relativa Aire

    sLine  = str(nEMA) + ',' + str(nMP01) + ',' + str(nMP25) + ',' + str(nMP10) + ','
    sLine += str(nHi03) + ',' + str(nHi05) + ',' + str(nHi01) + ','
    sLine += str(nHi25) + ',' + str(nHi50) + ',' + str(nHi10) + ','
    sLine += str(nTE) + ',' + str(nHR)
    return sLine


def send_direct_to_flask(sLine, url='http://127.0.0.1:7070/data'):
    """Modo opcional para probar el servidor Flask directamente sin puerto serial."""
    partes = [int(x) for x in sLine.split(',')]
    payload = {
        'id': partes[0],
        'mp01': partes[1],
        'mp02': partes[2],
        'mp03': partes[3],
        'hi01': partes[4],
        'hi02': partes[5],
        'hi03': partes[6],
        'hi04': partes[7],
        'hi05': partes[8],
        'hi06': partes[9],
        'te': partes[10],
        'hr': partes[11]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.read().decode('utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulador de Trama Serial PMS7003ST')
    parser.add_argument('--port', default='COM2', help='Puerto serial (ej. COM2 en Windows o /tmp/ttyV0 en Linux)')
    parser.add_argument('--baud', type=int, default=9600, help='Velocidad en baudios (por defecto 9600)')
    parser.add_argument('--interval', type=float, default=0.5, help=' Segundos entre tramas (por defecto 0.5s)')
    parser.add_argument('--http-only', action='store_true', help='Enviar datos directo al Server Flask por HTTP (sin puerto COM)')
    args = parser.parse_args()

    nId = 1

    if args.http_only:
        print("Iniciando simulación directa hacia Flask (http://127.0.0.1:7070/data)...")
        try:
            while True:
                sAux = Make_Data(nId)
                resp = send_direct_to_flask(sAux)
                print(f"Enviado a Flask -> {sAux} | Respuesta: {resp}")
                ti.sleep(args.interval)
                nId += 1
                if nId == 6:
                    nId = 1
        except KeyboardInterrupt:
            print("\nSimulación finalizada.")
    else:
        print(f"Abriendo puerto serial {args.port} a {args.baud} baudios...")
        MyCnx = rs.Serial(args.port, args.baud)
        try:
            while True:
                sAux = Make_Data(nId)
                print(sAux)
                # En Python 3 pyserial requiere bytes; agregamos salto de línea para el buffer serial
                MyCnx.write((sAux + '\r\n').encode('utf-8'))
                ti.sleep(args.interval)
                nId += 1
                if nId == 6:
                    nId = 1
        except KeyboardInterrupt:
            print("\nCerrando conexión serial...")
        finally:
            MyCnx.close()
