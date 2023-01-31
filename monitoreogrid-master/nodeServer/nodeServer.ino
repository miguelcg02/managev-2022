
#include <WiFi.h>


//https://robologs.net/2014/10/15/tutorial-de-arduino-y-mpu-6050/
//https://randomnerdtutorials.com/esp32-static-fixed-ip-address-arduino-ide/

#include "MPU9250.h"
#include "Waveshare_10Dof-D.h"
#include <ArduinoJson.h>

const int capacity = JSON_OBJECT_SIZE(15);
StaticJsonDocument<capacity> doc;


int16_t AcX, AcY, AcZ, GyX, GyY, GyZ;
//Ratios de conversion
#define A_R 16384.0
#define G_R 131.0
//Conversion de radianes a grados 180/PI
#define RAD_A_DEG = 57.295779
static uint32_t lastMillis = millis();

//Definicion Angulos
float Acc[2];
float Gy[2];
//float Gy_ant[2];
float Angle[2];
float mean_angle[2];
float mean_acc[3];
uint16_t counter = 1; 
//float alpha[2];

// an MPU9250 object with the MPU-9250 sensor on I2C bus 0 with address 0x68
MPU9250 IMU(Wire, 0x68);
int status;

int32_t s32PressureVal = 0, s32TemperatureVal = 0, s32AltitudeVal = 0;

// Replace with your network credentials
const char* ssid = "2018030011WTJO";
const char* password = "OVMSinit";

// Set web server port number to 80
WiFiServer server(80);

// Variable to store the HTTP request
String header;

// Auxiliar variables to store the current output state
String output26State = "off";
String output27State = "off";

// Set your Static IP address
IPAddress ip(192, 168, 4, 4);
// Set your Gateway IP address
IPAddress gateway();

IPAddress subnet();
IPAddress primaryDNS(8, 8, 8, 8);   //optional
IPAddress secondaryDNS(8, 8, 4, 4); //optional

// Assign output variables to GPIO pins

// Current time
unsigned long currentTime = millis();
// Previous time
unsigned long previousTime = 0;
// Define timeout time in milliseconds (example: 2000ms = 2s)
const long timeoutTime = 2000;

void setup() {
  Serial.begin(115200);
  while (!Serial) {}
  // start communication with IMU
  IMU_EN_SENSOR_TYPE enMotionSensorType, enPressureType;
  imuInit( &enMotionSensorType,  &enPressureType);
  status = IMU.begin();
  if (status < 0) {
    Serial.println("IMU initialization unsuccessful");
    Serial.println("Check IMU wiring or try cycling power");
    Serial.print("Status: ");
    Serial.println(status);
    while (1) {}
  }
  // setting the accelerometer full scale range to +/-8G
  IMU.setAccelRange(MPU9250::ACCEL_RANGE_8G);
  // setting the gyroscope full scale range to +/-500 deg/s
  IMU.setGyroRange(MPU9250::GYRO_RANGE_500DPS);
  // setting DLPF bandwidth to 20 Hz
  IMU.setDlpfBandwidth(MPU9250::DLPF_BANDWIDTH_20HZ);
  // setting SRD to 19 for a 50 Hz update rate
  IMU.setSrd(19);
  // Initialize the output variables as outputs

  // Configures static IP address local_IP, gateway, subnet, primaryDNS, secondaryDNS
//if (!WiFi.config()) {
//    Serial.println("STA Failed to configure");
//  }

  // Connect to Wi-Fi network with SSID and password
  //WiFi.config(ip, gateway, subnet );
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  // Print local IP address and start web server
  Serial.println("");
  Serial.println("WiFi connected.");

  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  server.begin();
}

void loop() {

  if (millis() - lastMillis > 50) {
    lastMillis = millis();
    IMU.readSensor();
    pressSensorDataGet(&s32TemperatureVal, &s32PressureVal, &s32AltitudeVal);

    AcX = IMU.getAccelX_mss();
    Serial.print("\t");
    AcY = IMU.getAccelY_mss();
    Serial.print("\t");
    AcZ = IMU.getAccelZ_mss();

    Acc[0] = atan((AcY / A_R) / sqrt(pow((AcX / A_R), 2) + pow((AcZ / A_R), 2))) * RAD_TO_DEG;
    Acc[1] = atan(-1 * (AcX / A_R) / sqrt(pow((AcY / A_R), 2) + pow((AcZ / A_R), 2))) * RAD_TO_DEG;

    GyX = IMU.getGyroX_rads();
    GyY = IMU.getGyroY_rads();

    //Calculo del angulo del Giroscopio
    Gy[0] = GyX / G_R;
    Gy[1] = GyY / G_R;

    Angle[0] = 0.98 * (Angle[0] + Gy[0] * 0.05) + 0.02 * Acc[0];  //dt = 0.05
    Angle[1] = 0.98 * (Angle[1] + Gy[1] * 0.05) + 0.02 * Acc[1];

    if (isnan(Angle[1])) {
      ESP.restart();
    }

    Serial.print(Angle[0], 6);
    Serial.print("  :----:  ");
    Serial.print(Angle[1], 6);
    Serial.print("  :----:  ");
    Serial.println(WiFi.localIP());
    mean_angle[0] += Angle[0];
    mean_angle[1] += Angle[1];
    mean_acc[0] += AcX;
    mean_acc[1] += AcY;
    mean_acc[2] += AcZ;
    counter++;
  }


  WiFiClient client = server.available();   // Listen for incoming clients

  //if (0) {
  if (client) {                             // If a new client connects,
    currentTime = millis();
    previousTime = currentTime;
    Serial.println("New Client.");          // print a message out in the serial port
    String currentLine = "";                // make a String to hold incoming data from the client
    while (client.connected() && currentTime - previousTime <= timeoutTime) {  // loop while the client's connected
      currentTime = millis();
      if (client.available()) {             // if there's bytes to read from the client,
        char c = client.read();             // read a byte, then
        Serial.write(c);                    // print it out the serial monitor
        header += c;
        if (c == '\n') {                    // if the byte is a newline character
          // if the current line is blank, you got two newline characters in a row.
          // that's the end of the client HTTP request, so send a response:
          if (currentLine.length() == 0) {
            // HTTP headers always start with a response code (e.g. HTTP/1.1 200 OK)
            // and a content-type so the client knows what's coming, then a blank line:
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println("Connection: close");
            client.println();

            if (header.indexOf("GET /data") >= 0) {
             
              doc["angle_x"] = round(mean_angle[0]/counter * 100.0) / 100.0;
              doc["angle_y"] = round(mean_angle[1]/counter * 100.0) / 100.0;
              doc["temp"] = round(IMU.getTemperature_C() * 100.0) / 100.0;
              doc["pressure"] = round((float)s32PressureVal / 100.0);
              doc["elevation2"] = round((float)s32AltitudeVal / 100.0);
              doc["AcX"] = round(mean_acc[0]/counter * 100.0) / 100.0;
              doc["AcY"] = round(mean_acc[1]/counter * 100.0) / 100.0;
              doc["AcZ"] = round(mean_acc[2]/counter * 100.0) / 100.0;
              
              serializeJson(doc, client);
              
              Serial.print(round(mean_angle[0]/counter * 100.0) / 100.0);
              Serial.print("----");
              Serial.println(round(mean_angle[1]/counter * 100.0) / 100.0);
              mean_angle[0] = 0;
              mean_angle[1] = 0;
              counter = 1;
              //client.println();
              //serializeJsonPretty(doc, client);
              // The HTTP response ends with another blank line
            }

            else {
              if (header.indexOf("GET /26/on") >= 0) {
                Serial.println("GPIO 26 on");
                output26State = "on";
              } else if (header.indexOf("GET /26/off") >= 0) {
                Serial.println("GPIO 26 off");
                output26State = "off";
              } else if (header.indexOf("GET /27/on") >= 0) {
                Serial.println("GPIO 27 on");
                output27State = "on";
              } else if (header.indexOf("GET /27/off") >= 0) {
                Serial.println("GPIO 27 off");
                output27State = "off";
              }

              // Display the HTML web page
              client.println("<!DOCTYPE html><html>");
              client.println("<head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">");
              client.println("<link rel=\"icon\" href=\"data:,\">");
              // CSS to style the on/off buttons
              // Feel free to change the background-color and font-size attributes to fit your preferences
              client.println("<style>html { font-family: Helvetica; display: inline-block; margin: 0px auto; text-align: center;}");
              client.println(".button { background-color: #4CAF50; border: none; color: white; padding: 16px 40px;");
              client.println("text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}");
              client.println(".button2 {background-color: #555555;}</style></head>");

              // Web Page Heading
              client.println("<body><h1>ESP32 Web Server</h1>");

              // Display current state, and ON/OFF buttons for GPIO 26
              client.println("<p>GPIO 26 - State " + output26State + "</p>");
              // If the output26State is off, it displays the ON button
              if (output26State == "off") {
                client.println("<p><a href=\"/26/on\"><button class=\"button\">ON</button></a></p>");
              } else {
                client.println("<p><a href=\"/26/off\"><button class=\"button button2\">OFF</button></a></p>");
              }

              // Display current state, and ON/OFF buttons for GPIO 27
              client.println("<p>GPIO 27 - State " + output27State + "</p>");
              // If the output27State is off, it displays the ON button
              if (output27State == "off") {
                client.println("<p><a href=\"/27/on\"><button class=\"button\">ON</button></a></p>");
              } else {
                client.println("<p><a href=\"/27/off\"><button class=\"button button2\">OFF</button></a></p>");
              }
              client.println("</body></html>");

              // The HTTP response ends with another blank line
              client.println();
              // Break out of the while loop
            }
            break;
          } else { // if you got a newline, then clear currentLine
            currentLine = "";
          }
        } else if (c != '\r') {  // if you got a  return character,
          currentLine += c;      // add it to the end of the currentLine
        }
      }
    }
    // Clear the header variable
    header = "";
    // Close the connection
    client.stop();
    Serial.println("Client disconnected.");
    Serial.println("");
  }
}
