// ============================================================
// WineGuard Node 2 - marcha.dev
// ESP32 + DHT22 + LDR + LED RGB + buzzer + OLED + botao de mute
//
// Base: projeto "FIWARE Smart Lamp" (Prof. Fabio H. Cabrini)
// Protocolo: Ultralight 2.0 via MQTT (FIWARE Descomplicado)
//
// Topicos:
//   /<API_KEY>/<DEVICE_ID>/attrs   -> telemetria (Node -> nuvem)
//   /<API_KEY>/<DEVICE_ID>/cmd     -> comandos   (nuvem -> Node)
//   /<API_KEY>/<DEVICE_ID>/cmdexe  -> resposta   (Node -> nuvem)
//
// Telemetria: t|24.5|h|60.0|l|35|st|ok|mu|0|rs|-60|fw|2.0
// Comandos  : <DEVICE_ID>@<comando>|<parametros separados por virgula>
//   setTriggers|tmin,tmax,hmin,hmax,lmin,lmax
//   alert|<t|h|l>,<high|low>,<1|0>
//   mute|<1|0>
//   suspend|            resume|
//   setInterval|<segundos>
//   identify|
//
// ARQUITETURA (FreeRTOS):
//   loop()           -> Wi-Fi, MQTT, sensores, botao, telemetria
//   tarefaAtuadores  -> LED + buzzer (tick de 2 ms, nunca bloqueia)
//   tarefaOled       -> tela (acompanha varAtual/emPausa)
// Assim o alarme continua igual mesmo se Wi-Fi/MQTT cairem.
//
// ALERTA ALTO  (acima): LED FIXO na cor da variavel; buzzer toca o padrao.
// ALERTA BAIXO (abaixo): LED PISCA na cor da variavel, junto com o
//                        buzzer, em ritmo 2x mais lento.
// ============================================================

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <Preferences.h>
#include "config.h"
#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif
#include "icones.h"   // icones 32x32 (termometro, gota, sol)

#define FW_VERSION "2.0"

// 1 = o Node avalia os limites sozinho, mesmo conectado (enquanto nao ha backend)
// 0 = so obedece aos comandos "alert" do backend (avalia sozinho apenas se ficar offline)
#define AVALIACAO_LOCAL_SEMPRE 1

// ---------------- Pinos ----------------
#define PIN_DHT      5    // DHT22 (D5)
#define PIN_LDR      34   // LDR (ADC1)
#define PIN_BUZZER   18
#define PIN_LED_R    25   // vermelho = temperatura
#define PIN_LED_G    26   // verde    = luminosidade
#define PIN_LED_B    27   // azul     = umidade
#define PIN_BOTAO    14   // mute
#define PIN_SDA      21
#define PIN_SCL      22

// ---------------- Ajustes de hardware ----------------
#define DHTTYPE DHT22
#define LDR_INVERTIDO 0          // 1 se "mais luz = numero menor" no seu modulo
#ifndef BUZZER_ATIVO_EM_LOW
#define BUZZER_ATIVO_EM_LOW 0    // 1 se o modulo apita com nivel baixo
#endif

#if SIMULACAO_WOKWI
  #define BOTAO_MODO        INPUT_PULLUP
  #define BOTAO_PRESSIONADO LOW
#else
  #define BOTAO_MODO        INPUT
  #define BOTAO_PRESSIONADO HIGH   // confirme no monitor serial com o seu modulo
#endif

#define OLED_LARGURA 128
#define OLED_ALTURA  64
#define OLED_ENDERECO 0x3C

// ---------------- Variaveis monitoradas ----------------
enum { V_TEMP = 0, V_UMID = 1, V_LUZ = 2 };
const char* NOMES_TELA[3]  = {"TEMPERATURA", "UMIDADE", "LUZ"};
const char* CORES_LED[3]   = {"VERM", "AZUL", "VERDE"};
const char* UNIDADES[3]    = {"C", "%", "%"};
const uint8_t DECIMAIS[3]  = {1, 0, 0};
const uint8_t PIN_LED_VAR[3] = {PIN_LED_R, PIN_LED_B, PIN_LED_G};

// Triggers: tmin, tmax, hmin, hmax, lmin, lmax (padrao = preset "Tinto")
const float TRIG_PADRAO[6] = {12.0, 16.0, 60.0, 75.0, 0.0, 10.0};
const float HISTERESE[3]   = {0.5, 2.0, 2.0};   // folga para sair do alerta

// Padroes de bipes (ms, alternando ligado/desligado, comecando ligado).
// O ultimo item e a pausa entre repeticoes.
// Acima  = padrao como definido abaixo (rapido).
// Abaixo = bipes e intervalos 2x mais longos (lento); a pausa nao muda.
const uint16_t PAD_TEMP[] = {700, 800};                 // 1 bipe longo
const uint16_t PAD_UMID[] = {150, 150, 150, 800};       // 2 bipes curtos
const uint16_t PAD_LUZ[]  = {80, 80, 80, 80, 80, 800};  // 3 bipes rapidos
const uint16_t* const PADROES[3] = {PAD_TEMP, PAD_UMID, PAD_LUZ};
const uint8_t TAM_PADRAO[3] = {2, 4, 6};

#define RODIZIO_MIN_MS    3000   // tempo minimo em cada variavel
#define PAUSA_TROCA_MS     700   // silencio total (LED, buzzer e tela) ao trocar

// ---------------- Objetos ----------------
WiFiClient espClient;
PubSubClient MQTT(espClient);
Adafruit_SSD1306 display(OLED_LARGURA, OLED_ALTURA, &Wire, -1);
DHT dht(PIN_DHT, DHTTYPE);
Preferences prefs;

char topicAttrs[64], topicCmd[64], topicCmdExe[64], clientId[40];

// ---------------- Estado ----------------
// "volatile": lidas/escritas por tarefas diferentes
volatile float temperatura = NAN, umidade = NAN;
volatile int   luz = 0;
volatile uint8_t alerta[3] = {0, 0, 0};   // 0 normal, 1 acima, 2 abaixo
volatile bool suspenso = false, mudo = false;
volatile bool emPausa = false;
volatile int  varAtual = -1;
volatile unsigned long identificaAte = 0;

// espelhos do estado de rede, atualizados so no loop() e lidos pela tela
volatile bool wifiOk = false, mqttOk = false, offlineLocal = false;

float trig[6];
unsigned long intervaloMs = 5000;

unsigned long tDht = 0, tPub = 0, tOled = 0;
unsigned long tWifiTentativa = 0, tMqttTentativa = 0, tUltimoMqttOk = 0;

// controle do rodizio de alertas (so a tarefaAtuadores mexe)
unsigned long tRodizio = 0, tPad = 0, tPausa = 0;
uint8_t padIdx = 0;
int proxVar = -1;

// ============================================================
//  Memoria (NVS)
// ============================================================
void carregaConfig() {
  prefs.begin("wineguard", false);
  char k[4];
  for (int i = 0; i < 6; i++) {
    snprintf(k, sizeof(k), "t%d", i);
    trig[i] = prefs.getFloat(k, TRIG_PADRAO[i]);
  }
  suspenso    = prefs.getBool("susp", false);
  mudo        = prefs.getBool("mudo", false);
  intervaloMs = prefs.getULong("intv", 5000);
}

void salvaTriggers() {
  char k[4];
  for (int i = 0; i < 6; i++) {
    snprintf(k, sizeof(k), "t%d", i);
    prefs.putFloat(k, trig[i]);
  }
}

// ============================================================
//  Atuadores (rodam na tarefaAtuadores)
// ============================================================
void buzzer(bool ligar) {
  static bool estado = false;
  if (ligar == estado) return;
  estado = ligar;
#if SIMULACAO_WOKWI
  if (ligar) tone(PIN_BUZZER, 2000);
  else noTone(PIN_BUZZER);
#else
  bool nivel = BUZZER_ATIVO_EM_LOW ? !ligar : ligar;
  digitalWrite(PIN_BUZZER, nivel ? HIGH : LOW);
#endif
}

void ledsApagados() {
  digitalWrite(PIN_LED_R, LOW);
  digitalWrite(PIN_LED_G, LOW);
  digitalWrite(PIN_LED_B, LOW);
}

// proxima variavel em alerta depois de "base" (circular). -1 se nenhuma.
int proximaVar(int base) {
  for (int k = 1; k <= 3; k++) {
    int c = (base + k) % 3;
    if (alerta[c]) return c;
  }
  return -1;
}

void iniciaPausa(int proxima) {
  emPausa = true;
  proxVar = proxima;
  tPausa = millis();
  ledsApagados();
  buzzer(false);
}

// duracao de cada passo do padrao; "abaixo" deixa tudo 2x mais lento
uint16_t duracaoPad(int v, uint8_t i) {
  uint16_t d = PADROES[v][i];
  if (alerta[v] == 2 && i < TAM_PADRAO[v] - 1) d *= 2;
  return d;
}

void atualizaAtuadores() {
  if (suspenso) {
    ledsApagados();
    buzzer(false);
    varAtual = -1;
    emPausa = false;
    return;
  }

  // identify: pisca tudo para achar o Node certo
  if (identificaAte > millis()) {
    bool on = (millis() / 250) % 2 == 0;
    digitalWrite(PIN_LED_R, on);
    digitalWrite(PIN_LED_G, on);
    digitalWrite(PIN_LED_B, on);
    buzzer(on && !mudo);
    return;
  }

  int n = (alerta[0] > 0) + (alerta[1] > 0) + (alerta[2] > 0);
  if (n == 0) {
    varAtual = -1;
    emPausa = false;
    ledsApagados();
    buzzer(false);
    return;
  }

  // --- pausa entre variaveis: LED, buzzer e tela em silencio ---
  if (emPausa) {
    ledsApagados();
    buzzer(false);
    if (millis() - tPausa >= PAUSA_TROCA_MS) {
      emPausa = false;
      varAtual = proxVar;
      padIdx = 0;
      tPad = millis();
      tRodizio = millis();
    }
    return;
  }

  // primeiro alerta: comeca direto, sem pausa
  if (varAtual < 0) {
    varAtual = proximaVar(-1);
    padIdx = 0;
    tPad = millis();
    tRodizio = millis();
  }
  // a variavel atual voltou ao normal: passa para a proxima (com pausa)
  else if (alerta[varAtual] == 0) {
    iniciaPausa(proximaVar(varAtual));
    return;
  }

  int v = varAtual;
  bool bipe = (padIdx % 2 == 0);
  bool alta = (alerta[v] == 1);

  ledsApagados();
  if (alta) {
    // ALTO: LED fixo na cor da variavel durante todo o tempo dela
    digitalWrite(PIN_LED_VAR[v], HIGH);
  } else {
    // BAIXO: LED pisca junto com o buzzer
    if (bipe) digitalWrite(PIN_LED_VAR[v], HIGH);
  }
  buzzer(bipe && !mudo);   // mudo silencia so o buzzer

  // ritmo sem deriva: soma a duracao em vez de reler millis()
  unsigned long dur = duracaoPad(v, padIdx);
  if (millis() - tPad >= dur) {
    tPad += dur;
    padIdx = (padIdx + 1) % TAM_PADRAO[v];
    // terminou um ciclo completo: se ha outro alerta e o tempo minimo passou, troca
    if (padIdx == 0 && n > 1 && millis() - tRodizio >= RODIZIO_MIN_MS) {
      iniciaPausa(proximaVar(v));
    }
  }
}

void tarefaAtuadores(void*) {
  for (;;) {
    atualizaAtuadores();
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

// ============================================================
//  Sensores
// ============================================================
void leSensores() {
  if (millis() - tDht < 2000) return;   // DHT22: no maximo 1 leitura a cada 2 s
  tDht = millis();

  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) temperatura = t;
  if (!isnan(h)) umidade = h;

  long soma = 0;
  for (int i = 0; i < 8; i++) soma += analogRead(PIN_LDR);   // media reduz ruido
  int pct = map(soma / 8, 0, 4095, 0, 100);
  if (LDR_INVERTIDO) pct = 100 - pct;
  luz = constrain(pct, 0, 100);
}

// ============================================================
//  Failsafe: avaliacao local quando a nuvem esta fora do ar
// ============================================================
uint8_t avalia(float v, float mn, float mx, float hist, uint8_t atual) {
  if (atual == 0) {
    if (v > mx) return 1;
    if (v < mn) return 2;
  } else if (atual == 1) {
    if (v <= mx - hist) return 0;
  } else {
    if (v >= mn + hist) return 0;
  }
  return atual;
}

void avaliaLocal() {
  float t = temperatura, h = umidade;
  if (!isnan(t)) alerta[V_TEMP] = avalia(t, trig[0], trig[1], HISTERESE[V_TEMP], alerta[V_TEMP]);
  if (!isnan(h)) alerta[V_UMID] = avalia(h, trig[2], trig[3], HISTERESE[V_UMID], alerta[V_UMID]);
  alerta[V_LUZ] = avalia((float)luz, trig[4], trig[5], HISTERESE[V_LUZ], alerta[V_LUZ]);
}

// ============================================================
//  Botao de mute (alterna, com debounce)
// ============================================================
void tratarBotao() {
  static bool ultimo = false;
  static unsigned long t = 0;
  bool pressionado = (digitalRead(PIN_BOTAO) == BOTAO_PRESSIONADO);
  if (pressionado && !ultimo && millis() - t > 250) {
    mudo = !mudo;
    prefs.putBool("mudo", mudo);
    t = millis();
    Serial.println(mudo ? "- Mute ligado (botao)" : "- Mute desligado (botao)");
  }
  ultimo = pressionado;
}

// ============================================================
//  Comandos recebidos por MQTT
// ============================================================
bool parseFloats(const String& s, float* out, int n) {
  int pos = 0;
  for (int i = 0; i < n; i++) {
    int virg = s.indexOf(',', pos);
    String parte = (virg < 0) ? s.substring(pos) : s.substring(pos, virg);
    if (parte.length() == 0) return false;
    out[i] = parte.toFloat();
    if (virg < 0) return i == n - 1;
    pos = virg + 1;
  }
  return true;
}

bool executaComando(const String& cmd, const String& params) {
  if (cmd == "setTriggers") {
    float v[6];
    if (!parseFloats(params, v, 6)) return false;
    for (int i = 0; i < 6; i++) trig[i] = v[i];
    salvaTriggers();
    return true;
  }

  if (cmd == "alert") {
    int s1 = params.indexOf(',');
    int s2 = params.indexOf(',', s1 + 1);
    if (s1 < 0 || s2 < 0) return false;
    char c = params.charAt(0);
    String dir = params.substring(s1 + 1, s2);
    int on = params.substring(s2 + 1).toInt();
    int idx = (c == 't') ? V_TEMP : (c == 'h') ? V_UMID : (c == 'l') ? V_LUZ : -1;
    if (idx < 0 || (dir != "high" && dir != "low")) return false;
    alerta[idx] = on ? (dir == "high" ? 1 : 2) : 0;
    return true;
  }

  if (cmd == "mute") {
    mudo = (params.toInt() == 1);
    prefs.putBool("mudo", mudo);
    return true;
  }

  if (cmd == "suspend") {
    suspenso = true;
    alerta[0] = alerta[1] = alerta[2] = 0;
    prefs.putBool("susp", true);
    return true;
  }

  if (cmd == "resume") {
    suspenso = false;
    prefs.putBool("susp", false);
    tPub = 0;   // publica logo
    return true;
  }

  if (cmd == "setInterval") {
    long s = params.toInt();
    if (s < 2 || s > 3600) return false;
    intervaloMs = s * 1000UL;
    prefs.putULong("intv", intervaloMs);
    return true;
  }

  if (cmd == "identify") {
    identificaAte = millis() + 5000;
    return true;
  }

  return false;
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.print("- Mensagem recebida: ");
  Serial.println(msg);

  // formato: <device>@<comando>|<parametros>
  int at = msg.indexOf('@');
  int bar = msg.indexOf('|');
  if (at < 0 || bar < 0) return;
  String dev = msg.substring(0, at);
  String cmd = msg.substring(at + 1, bar);
  String params = msg.substring(bar + 1);
  if (dev != DEVICE_ID) return;

  bool ok = executaComando(cmd, params);

  String resp = String(DEVICE_ID) + "@" + cmd + "|" + (ok ? "ok" : "erro");
  MQTT.publish(topicCmdExe, resp.c_str());
}

// ============================================================
//  Conexao (sem bloquear o loop)
// ============================================================
void conectaRede() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (tWifiTentativa != 0 && millis() - tWifiTentativa < 10000) return;
  tWifiTentativa = millis();
  Serial.print("Conectando ao Wi-Fi: ");
  Serial.println(WIFI_SSID);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void conectaMqtt() {
  if (WiFi.status() != WL_CONNECTED || MQTT.connected()) return;
  if (tMqttTentativa != 0 && millis() - tMqttTentativa < 5000) return;
  tMqttTentativa = millis();
  Serial.print("* Conectando ao broker: ");
  Serial.println(MQTT_BROKER);
  if (MQTT.connect(clientId)) {
    Serial.println("Conectado ao broker MQTT!");
    MQTT.subscribe(topicCmd);
    tPub = 0;   // publica o estado assim que conectar
    // OBS para o backend: ao ver o Node voltar a publicar, reenviar o estado
    // atual dos alertas (o Node so recebe comandos nas transicoes).
  } else {
    Serial.println("Falha no broker, nova tentativa em 5 s");
  }
}

// ============================================================
//  Telemetria
// ============================================================
const char* estadoTexto() {
  if (suspenso) return "suspenso";
  if (alerta[0] || alerta[1] || alerta[2]) return "alerta";
  return "ok";
}

void publicaTelemetria() {
  if (!MQTT.connected() || suspenso) return;
  if (millis() - tPub < intervaloMs) return;
  if (isnan(temperatura) || isnan(umidade)) return;   // espera a 1a leitura valida
  tPub = millis();

  char msg[160];
  snprintf(msg, sizeof(msg), "t|%.1f|h|%.1f|l|%d|st|%s|mu|%d|rs|%d|fw|%s",
           (float)temperatura, (float)umidade, (int)luz, estadoTexto(), mudo ? 1 : 0,
           WiFi.RSSI(), FW_VERSION);
  MQTT.publish(topicAttrs, msg);
  Serial.print("- Enviado: ");
  Serial.println(msg);
}

// ============================================================
//  OLED (roda na tarefaOled; so ela usa o display)
// ============================================================
void telaStatus() {
  display.setTextSize(1);
  display.println("WineGuard Node");
  display.println(NOME_VINHERIA);
  display.println(NOME_ADEGA);
  display.print("ID: ");
  display.println(DEVICE_ID);
  display.print("WiFi: ");
  display.println(wifiOk ? "ok" : "sem rede");
  display.print("MQTT: ");
  display.println(mqttOk ? "ok" : (offlineLocal ? "OFFLINE (local)" : "..."));
  if (mudo) display.println("MUDO");
}

void telaValores() {
  float t = temperatura, h = umidade;
  display.setTextSize(2);

  // linha 1: temperatura (icone 16x16 + valor)
  display.drawBitmap(0, 0, ICO16_TEMP, ICO16_W, ICO16_H, SSD1306_WHITE);
  display.setCursor(22, 0);
  if (isnan(t)) display.print("--"); else display.print(t, 1);
  display.print(" C");

  // linha 2: umidade
  display.drawBitmap(0, 24, ICO16_UMID, ICO16_W, ICO16_H, SSD1306_WHITE);
  display.setCursor(22, 24);
  if (isnan(h)) display.print("--"); else display.print(h, 0);
  display.print(" %");

  // linha 3: luz
  display.drawBitmap(0, 48, ICO16_LUZ, ICO16_W, ICO16_H, SSD1306_WHITE);
  display.setCursor(22, 48);
  display.print((int)luz);
  display.print(" %");

  if (mudo) {
    display.setTextSize(1);
    display.setCursor(98, 56);
    display.print("MUDO");
  }
}

float valorVar(int v) {
  if (v == V_TEMP) return temperatura;
  if (v == V_UMID) return umidade;
  return (float)luz;
}

// Tela cheia de UMA variavel em alerta: a mesma (varAtual) que esta
// acendendo o LED e tocando o buzzer naquele momento.
void telaAlerta(int v) {
  bool alta = (alerta[v] == 1);

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(NOMES_TELA[v]);
  display.print(" [");
  display.print(CORES_LED[v]);
  display.print("]");

  display.setTextSize(3);
  display.setCursor(0, 12);
  display.print(alta ? "ALTA" : "BAIXA");

  // icone da variavel ao lado de ALTA/BAIXA
  const unsigned char* ico = (v == V_TEMP) ? ICO_TEMP : (v == V_UMID) ? ICO_UMID : ICO_LUZ;
  display.drawBitmap(96, 14, ico, ICO_W, ICO_H, SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 40);
  float val = valorVar(v);
  if (isnan(val)) display.print("--");
  else display.print(val, DECIMAIS[v]);
  display.print(" ");
  display.print(UNIDADES[v]);

  display.setTextSize(1);
  display.setCursor(0, 56);
  display.print(alta ? "Max " : "Min ");
  display.print(trig[2 * v + (alta ? 1 : 0)], DECIMAIS[v]);
  display.print(UNIDADES[v]);

  int n = 0, pos = 0;
  for (int i = 0; i < 3; i++) {
    if (alerta[i]) { n++; if (i <= v) pos++; }
  }
  if (n > 1) {
    display.setCursor(78, 56);
    display.print(pos);
    display.print("/");
    display.print(n);
  }
  if (mudo) {
    display.setCursor(98, 56);
    display.print("MUDO");
  }
}

void desenhaOled() {
  static int ultimaChave = -9;
  // atualiza a cada 250 ms, ou na hora se mudou a variavel ou entrou/saiu da pausa
  int va = varAtual;
  bool pausa = emPausa;
  int chave = pausa ? -3 : va;
  if (millis() - tOled < 250 && chave == ultimaChave) return;
  tOled = millis();
  ultimaChave = chave;

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

  if (pausa && !suspenso) {
    // pausa entre variaveis: tela apagada junto com LED e buzzer
  } else if (suspenso) {
    display.setTextSize(1);
    display.println("WineGuard");
    display.setTextSize(2);
    display.setCursor(0, 20);
    display.println("Servico");
    display.println("suspenso");
  } else {
    if (va >= 0 && alerta[va]) {
      telaAlerta(va);
    } else {
      int tela = (millis() / 4000) % 2;   // sem alerta: alterna a cada 4 s
      if (tela == 0) telaStatus(); else telaValores();
    }
  }
  display.display();
}

void tarefaOled(void*) {
  for (;;) {
    desenhaOled();
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

void splash() {
  // 1) logo
  display.clearDisplay();
  display.drawBitmap((OLED_LARGURA - LOGO_W) / 2, 0, LOGO, LOGO_W, LOGO_H, SSD1306_WHITE);
  display.display();
  delay(1500);

  // 2) boas-vindas (a setup() segura esta tela por mais 2 s)
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Bem-vindo ao");
  display.setTextSize(2);
  display.setCursor(0, 14);
  display.println("WineGuard");
  display.setTextSize(1);
  display.setCursor(0, 40);
  display.println("Cada garrafa no");
  display.println("ponto certo.");
  display.display();
}

// ============================================================
//  setup / loop
// ============================================================
void setup() {
  Serial.begin(115200);

  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_B, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BOTAO, BOTAO_MODO);
  ledsApagados();
#if !SIMULACAO_WOKWI
  digitalWrite(PIN_BUZZER, BUZZER_ATIVO_EM_LOW ? HIGH : LOW);
#endif

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);   // tela ~4x mais rapida
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ENDERECO)) {
    Serial.println("OLED nao encontrado (confira SDA/SCL e o endereco 0x3C)");
  }
  splash();

  dht.begin();
  carregaConfig();

  snprintf(topicAttrs, sizeof(topicAttrs), "/%s/%s/attrs", API_KEY, DEVICE_ID);
  snprintf(topicCmd, sizeof(topicCmd), "/%s/%s/cmd", API_KEY, DEVICE_ID);
  snprintf(topicCmdExe, sizeof(topicCmdExe), "/%s/%s/cmdexe", API_KEY, DEVICE_ID);
  snprintf(clientId, sizeof(clientId), "wineguard_%s", DEVICE_ID);

  WiFi.mode(WIFI_STA);
  MQTT.setServer(MQTT_BROKER, MQTT_PORT);
  MQTT.setCallback(mqttCallback);
  MQTT.setSocketTimeout(2);   // connect() nao trava mais ~15 s

  delay(2000);   // so para mostrar o splash

  // LED/buzzer e tela rodam por conta propria, independentes da rede
  xTaskCreatePinnedToCore(tarefaAtuadores, "atuad", 4096, NULL, 2, NULL, 1);
  xTaskCreatePinnedToCore(tarefaOled,      "oled",  4096, NULL, 1, NULL, 1);
}

void loop() {
  conectaRede();
  conectaMqtt();
  MQTT.loop();

  bool mq = MQTT.connected();
  if (mq) tUltimoMqttOk = millis();
  wifiOk = (WiFi.status() == WL_CONNECTED);
  mqttOk = mq;
  offlineLocal = !mq && (millis() - tUltimoMqttOk > 15000UL);

  tratarBotao();
  leSensores();
  if ((AVALIACAO_LOCAL_SEMPRE || offlineLocal) && !suspenso) avaliaLocal();
  publicaTelemetria();
  // atualizaAtuadores() e desenhaOled() rodam nas tarefas
}
