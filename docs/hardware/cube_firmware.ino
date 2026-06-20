/*
 * cube_firmware.ino — SCBE cube hardware bridge, reference firmware.
 *
 * Reads a DIY cube and emits the SCBE wire protocol over USB serial so
 * `scbe bopit --serial <port>` turns physical twists into spoken commands.
 *
 * Wiring (this reference = the simplest buildable input stage):
 *   - 6 momentary inputs, one per face, to GPIO (active-low, INPUT_PULLUP):
 *       U,R,F,D,L,B  -> FACE_PINS below
 *   - 1 direction toggle (held = counter-clockwise) -> DIR_PIN
 *   - 1 commit button (run the program) -> GO_PIN
 *
 * Adapt the read stage to your real sensors:
 *   - hall-effect sensors / magnets on each face cap,
 *   - rotary encoders per face (gives direction for free),
 *   - or an MPU-6050 + gesture classifier (one IMU, infer face from axis).
 * Whatever you use, just Serial.println() the wire token ("R", "U'", "F2", "GO").
 *
 * Works on Arduino Uno/Nano and ESP32 alike. Baud 115200.
 */

const char  FACES[6]     = {'U', 'R', 'F', 'D', 'L', 'B'};
const int   FACE_PINS[6] = {2, 3, 4, 5, 6, 7};   // one input per face
const int   DIR_PIN      = 8;                     // held LOW = counter-clockwise (')
const int   GO_PIN       = 9;                     // press = commit (emit "GO")

const unsigned long DEBOUNCE_MS = 25;
int  lastFace[6];
int  lastGo;
unsigned long lastChange[6];
unsigned long lastGoChange;

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 6; i++) {
    pinMode(FACE_PINS[i], INPUT_PULLUP);
    lastFace[i] = HIGH;
    lastChange[i] = 0;
  }
  pinMode(DIR_PIN, INPUT_PULLUP);
  pinMode(GO_PIN, INPUT_PULLUP);
  lastGo = HIGH;
  lastGoChange = 0;
}

void emitFace(int i) {
  // print "<FACE>" or "<FACE>'" depending on the direction toggle
  Serial.print(FACES[i]);
  if (digitalRead(DIR_PIN) == LOW) Serial.print('\'');
  Serial.print('\n');
}

void loop() {
  unsigned long now = millis();

  for (int i = 0; i < 6; i++) {
    int s = digitalRead(FACE_PINS[i]);
    if (s != lastFace[i] && (now - lastChange[i]) > DEBOUNCE_MS) {
      lastChange[i] = now;
      lastFace[i] = s;
      if (s == LOW) emitFace(i);   // fire on press (a "twist")
    }
  }

  int g = digitalRead(GO_PIN);
  if (g != lastGo && (now - lastGoChange) > DEBOUNCE_MS) {
    lastGoChange = now;
    lastGo = g;
    if (g == LOW) Serial.print("GO\n");
  }
}
