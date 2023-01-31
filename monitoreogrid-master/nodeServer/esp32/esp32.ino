//https://robologs.net/2014/10/15/tutorial-de-arduino-y-mpu-6050/
int16_t AcX, AcY, AcZ, GyX, GyY, GyZ;

//Ratios de conversion
#define A_R 16384.0
#define G_R 131.0

//Conversion de radianes a grados 180/PI
#define RAD_A_DEG = 57.295779

//Angulos
float Acc[2];
float Gy[2];
float Angle[2];

#include "MPU9250.h"
#include "Waveshare_10Dof-D.h"

// an MPU9250 object with the MPU-9250 sensor on I2C bus 0 with address 0x68
MPU9250 IMU(Wire, 0x68);
int status;

void setup() {
  // serial to display data
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
}

void loop() {
  // read the sensor
  IMU.readSensor();
  int32_t s32PressureVal = 0, s32TemperatureVal = 0, s32AltitudeVal = 0;
  pressSensorDataGet(&s32TemperatureVal, &s32PressureVal, &s32AltitudeVal);
  
  AcX = IMU.getAccelX_mss();
  Serial.print("\t");
  AcY = IMU.getAccelY_mss();
  Serial.print("\t");
  AcZ = IMU.getAccelZ_mss();

  Acc[1] = atan(-1 * (AcX / A_R) / sqrt(pow((AcY / A_R), 2) + pow((AcZ / A_R), 2))) * RAD_TO_DEG;
  Acc[0] = atan((AcY / A_R) / sqrt(pow((AcX / A_R), 2) + pow((AcZ / A_R), 2))) * RAD_TO_DEG;

  GyX = IMU.getGyroX_rads();
  GyY = IMU.getGyroY_rads();


  //Calculo del angulo del Giroscopio
  Gy[0] = GyX / G_R;
  Gy[1] = GyY / G_R;

  Angle[0] = 0.97 * (Angle[0] + Gy[0] * 0.010) + 0.03 * Acc[0];
  Angle[1] = 0.97 * (Angle[1] + Gy[1] * 0.015) + 0.04 * Acc[1];


  //Mostrar los valores por consola
  Serial.print(" Angle X: "); Serial.print(Angle[0], 3); 
  Serial.print(" Angle Y: "); Serial.print(Angle[1], 3); 
  Serial.print(" Temp: "); Serial.print(IMU.getTemperature_C(), 3); 
  Serial.print(" Pressure: "); Serial.print((float)s32PressureVal / 100 , 3); 
  Serial.print(" Altitude: "); Serial.print((float)s32AltitudeVal / 100 , 3); 
  Serial.print(" Temperature 2: "); Serial.print((float)s32TemperatureVal / 100 , 3);
  Serial.println("-------");

  delay(10);
}
