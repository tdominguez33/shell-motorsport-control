/*
  Programa utilizado para emular un auto de la colección "Shell Motorsport"
  Si se ejecuta este programa en un ESP-32 y se utiliza la aplicación "Shell Racing" esta detectará al ESP-32 como si fuese un auto
  El ESP-32 luego imprime todos los comando recibidos en el monitor serie
  Permite obtener los comandos que espera recibir el auto para luego enviarselos por otros medios
*/

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#define SERVICE_UUID_1        "0000FFF0-0000-1000-8000-00805F9B34FB"
#define SERVICE_UUID_2        "0000FD00-0000-1000-8000-00805F9B34FB"
#define CHARACTERISTIC_UUID_1 "d44bc439-abfd-45a2-b575-925416129600"
#define CHARACTERISTIC_UUID_2 "d44bc439-abfd-45a2-b575-92541612960a"
#define CHARACTERISTIC_UUID_3 "d44bc439-abfd-45a2-b575-92541612960b"
#define CHARACTERISTIC_UUID_4 "d44bc439-abfd-45a2-b575-925416129601"
#define CHARACTERISTIC_UUID_5 "0000FD01-0000-1000-8000-00805F9B34FB"
#define CHARACTERISTIC_UUID_6 "0000FD02-0000-1000-8000-00805F9B34FB"

class MyCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) override {
        String value = pCharacteristic->getValue();
        Serial.print("Characteristic ");
        Serial.print(pCharacteristic->getUUID().toString().c_str());
        Serial.print(" received value in binary: ");

        for (char c : value) {
            // Recorre cada bit del carácter y lo imprime
            for (int i = 7; i >= 0; i--) {
                Serial.print((c >> i) & 1);
            }
            //Serial.print(" "); // Espacio entre bytes para mejor legibilidad
        }
        Serial.println();
    }

    void onRead(BLECharacteristic *pCharacteristic) override {
        Serial.print("Characteristic ");
        Serial.print(pCharacteristic->getUUID().toString().c_str());
        Serial.println(" was read.");
        
        String value = pCharacteristic->getValue().c_str(); // Obtener el valor actual de la característica
        Serial.print("Value being read: ");
        
        for (char c : value) {
            Serial.print((uint8_t)c);  // Imprimir cada byte en decimal
            Serial.print(" ");
        }
        Serial.println();
    }
};

void setup() {
    Serial.begin(115200);
    Serial.println("Starting BLE work!");

    BLEDevice::init("QCAR-2F3440");
    BLEServer *pServer = BLEDevice::createServer();

    BLEService *pService_1 = pServer->createService(SERVICE_UUID_1);
    BLECharacteristic *pCharacteristic_1 = pService_1->createCharacteristic(CHARACTERISTIC_UUID_1, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    BLECharacteristic *pCharacteristic_2 = pService_1->createCharacteristic(CHARACTERISTIC_UUID_2, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    BLECharacteristic *pCharacteristic_3 = pService_1->createCharacteristic(CHARACTERISTIC_UUID_3, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    BLECharacteristic *pCharacteristic_4 = pService_1->createCharacteristic(CHARACTERISTIC_UUID_4, BLECharacteristic::PROPERTY_NOTIFY);

    pCharacteristic_1->setCallbacks(new MyCallbacks());
    pCharacteristic_2->setCallbacks(new MyCallbacks());
    pCharacteristic_3->setCallbacks(new MyCallbacks());

    BLEDescriptor *pDescriptor_1 = new BLEDescriptor("2901");
    pDescriptor_1->setValue("TR1911R02-08A");
    pCharacteristic_1->addDescriptor(pDescriptor_1);

    BLEDescriptor *pDescriptor_2 = new BLEDescriptor("2901");
    pDescriptor_2->setValue("11A");
    pCharacteristic_2->addDescriptor(pDescriptor_2);

    BLEDescriptor *pDescriptor_3 = new BLEDescriptor("2901");
    pCharacteristic_3->addDescriptor(pDescriptor_3);

    BLEDescriptor *pDescriptor_4 = new BLEDescriptor("2902");
    pCharacteristic_4->addDescriptor(pDescriptor_4);

    BLEService *pService_2 = pServer->createService(SERVICE_UUID_2);
    BLECharacteristic *pCharacteristic_5 = pService_2->createCharacteristic(CHARACTERISTIC_UUID_5, BLECharacteristic::PROPERTY_WRITE_NR);
    BLECharacteristic *pCharacteristic_6 = pService_2->createCharacteristic(CHARACTERISTIC_UUID_6, BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_WRITE);

    // Callback para las características del segundo servicio
    pCharacteristic_5->setCallbacks(new MyCallbacks());
    pCharacteristic_6->setCallbacks(new MyCallbacks());

    BLEDescriptor *pDescriptor_6 = new BLEDescriptor("2902");
    pCharacteristic_6->addDescriptor(pDescriptor_6);

    pService_1->start();
    pService_2->start();

    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID_1);
    pAdvertising->addServiceUUID(SERVICE_UUID_2);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);

    unsigned long binario = 0b01010100010100100000000000111100;
    String result = "";
    for (int i = 24; i >= 0; i -= 8) {
        char byteChar = (binario >> i) & 0xFF;
        result += byteChar;
    }

    BLEAdvertisementData advertisementData;
    advertisementData.setManufacturerData(result);
    advertisementData.setShortName("QCAR-2F3440");
    pAdvertising->setAdvertisementData(advertisementData);

    BLEDevice::startAdvertising();
    Serial.println("Configuración Lista, ya se puede abrir la aplicación de Shell Racing!");
}

void loop() {
    delay(2000);
}
