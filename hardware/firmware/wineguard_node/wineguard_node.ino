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
// Telemetria: t|24.5|h|60.0|l|35|st|ok|mu|0|rs|-60|fw|2.3
// Comandos  : <DEVICE_ID>@<comando>|<parametros separados por virgula>
//   setTriggers|tmin,tmax,hmin,hmax,lmin,lmax
//   alert|<t|h|l>,<high|low>,<1|0>
//   mute|<1|0>
//   suspend|            resume|
//   setInterval|<segundos>
//   identify|
//
// ARQUITETURA (FreeRTOS):
//   loop()           -> Wi-Fi, MQTT, sensores, telemetria
//   tarefaAtuadores  -> botao + LED + buzzer (tick de 2 ms, nunca bloqueia)
//   tarefaOled       -> tela (acompanha varAtual/emPausa)
// Assim o alarme e o botao continuam iguais mesmo se Wi-Fi/MQTT cairem.
//
// COMO O ALERTA E COMUNICADO
//   Qual variavel : cor do LED (vermelho = temperatura, azul = umidade, verde = luz)
//                   e a tela do OLED.
//   Qual sentido  : o SOM e o LED.
//     ALTA  (acima) : LED FIXO; buzzer em tom CONTINUO (ou 1 bipe longo, ver ALTA_CONTINUO).
//     BAIXA (abaixo): LED PISCA junto com o buzzer; 2 bipes e uma pausa.
//   Com mais de um alerta, alterna entre as variaveis (com uma pausa de silencio).
//
// Historico:
//   2.1  sinal do LDR corrigido (0 % = escuro, 100 % = muita luz);
//        limites padrao alinhados ao preset "Guarda geral".
//   2.2  botao de mute lido na tarefa dos atuadores.
//   2.3  botao: descobre sozinho a polaridade do modulo, usa resistor interno
//        quando precisa e confirma o aperto por ~20 ms (nao confunde ruido com aperto);
//        buzzer simplificado: ALTA = tom continuo, BAIXA = 2 bipes.
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

#define FW_VERSION "2.3"

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

// LDR: 1 = "mais luz = numero MENOR" no sinal do modulo. E o caso do Wokwi e dos
// modulos LDR comuns (a saida fica alta no escuro). O firmware inverte para que
// 0 % = escuro e 100 % = muita luz.
// Se o seu modulo fisico for o contrario (o valor SOBE ao cobrir o sensor com a mao),
// coloque  #define LDR_INVERTIDO 0  no config.h.
#ifndef LDR_INVERTIDO
#define LDR_INVERTIDO 1
#endif

// Buzzer ativo de 3 pinos: muitos modulos apitam com nivel BAIXO.
// Se o buzzer apitar direto em repouso, coloque  #define BUZZER_ATIVO_EM_LOW 1  no config.h.
#ifndef BUZZER_ATIVO_EM_LOW
#define BUZZER_ATIVO_EM_LOW 0
#endif

// Alerta ALTO: 1 = tom continuo (fixo); 0 = 1 bipe longo repetido (menos incomodo).
#ifndef ALTA_CONTINUO
#define ALTA_CONTINUO 1
#endif

// Botao: a polaridade e descoberta sozinha ao ligar (NAO aperte o botao nessa hora).
// Para forcar, coloque no config.h:  #define BOTAO_PRESSIONADO HIGH  (ou LOW).

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

// Triggers: tmin, tmax, hmin, hmax, lmin, lmax
// Padrao = preset "Guarda geral" do dashboard (usado ate o Node receber os limites do backend)
const float TRIG_PADRAO[6] = {10.0, 15.0, 60.0, 75.0, 0.0, 10.0};
const float HISTERESE[3]   = {0.5, 2.0, 2.0};   // folga para sair do alerta

// Padroes de bipes (ms, alternando ligado/desligado, comecando ligado).
// O ultimo item e a pausa entre repeticoes. Bipes abaixo de ~100 ms se misturam
// no buzzer fisico, entao os tempos abaixo sao propositalmente generosos.
const uint16_t PAD_ALTA[]  = {600, 600};                // so se ALTA_CONTINUO 0: 1 bipe longo
const uint16_t PAD_BAIXA[] = {300, 250, 300, 1000};     // 2 bipes + pausa
const uint8_t TAM_PAD_ALTA  = 2;
const uint8_t TAM_PAD_BAIXA = 4;

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
volatile bool mudoPendente = false;       // botao mudou o mudo: o loop() grava na memoria
volatile bool emPausa = false;
volatile int  varAtual = -1;
volatile unsigned long identificaAte = 0;

// espelhos do estado de rede, atualizados so no loop() e lidos pela tela
volatile bool wifiOk = false, mqttOk = false, offlineLocal = false;

// botao: true = em repouso o pino fica em HIGH (aperta = LOW); false = repouso LOW (aperta = HIGH)
bool botaoRepousoAlto = false;

float trig[6];
unsigned long intervaloMs = 5000;

unsigned long tDht = 0, tPub = 0, tOled = 0;
unsigned long tWifiTentativa = 0, tMqttTentativa = 0, tUltimoMqttOk = 0;

// controle do rodizio de alertas (so a tarefaAtuadores mexe)
unsigned long tRodizio = 0, tPad = 0, tPausa = 0;
uint8_t padIdx = 0;
int proxVar = -1;

void tratarBotao();   // definida mais abaixo; usada pela tarefaAtuadores

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
  bool alta = (alerta[v] == 1);
  bool continuo = alta && ALTA_CONTINUO;

  const uint16_t* pad = alta ? PAD_ALTA : PAD_BAIXA;
  uint8_t tam = alta ? TAM_PAD_ALTA : TAM_PAD_BAIXA;
  if (padIdx >= tam) padIdx = 0;   // protege se o sentido mudou no meio do padrao

  bool bipe = continuo ? true : (padIdx % 2 == 0);

  ledsApagados();
  if (alta) {
    // ALTA: LED fixo na cor da variavel durante todo o tempo dela
    digitalWrite(PIN_LED_VAR[v], HIGH);
  } else {
    // BAIXA: LED pisca junto com o buzzer
    if (bipe) digitalWrite(PIN_LED_VAR[v], HIGH);
  }
  buzzer(bipe && !mudo);   // mudo silencia so o buzzer

  if (continuo) {
    // tom continuo: so ha troca de variavel pelo tempo
    if (n > 1 && millis() - tRodizio >= RODIZIO_MIN_MS) iniciaPausa(proximaVar(v));
    return;
  }

  // ritmo sem deriva: soma a duracao em vez de reler millis()
  unsigned long dur = pad[padIdx];
  if (millis() - tPad >= dur) {
    tPad += dur;
    padIdx = (padIdx + 1) % tam;
    // terminou um ciclo completo: se ha outro alerta e o tempo minimo passou, troca
    if (padIdx == 0 && n > 1 && millis() - tRodizio >= RODIZIO_MIN_MS) {
      iniciaPausa(proximaVar(v));
    }
  }
}

void tarefaAtuadores(void*) {
  for (;;) {
    tratarBotao();        // o botao fica aqui para nunca perder um aperto, mesmo com a rede travando o loop()
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
  if (LDR_INVERTIDO) pct = 100 - pct;   // modulo comum: escuro = valor alto, entao inverte
  luz = constrain(pct, 0, 100);         // 0 % = escuro, 100 % = muita luz
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
//  Botao de mute
// ============================================================

// Le o pino varias vezes e devolve quantas vezes leu HIGH (0 a 20).
int contaAltos(uint8_t modo) {
  pinMode(PIN_BOTAO, modo);
  delay(20);
  int altos = 0;
  for (int i = 0; i < 20; i++) {
    altos += digitalRead(PIN_BOTAO);
    delay(1);
  }
  return altos;
}

// Descobre como o modulo do botao esta ligado, olhando o nivel em REPOUSO.
// Modulos de 3 pinos variam: uns ficam em HIGH e vao a LOW ao apertar, outros o contrario.
void detectaBotao() {
#if SIMULACAO_WOKWI
  pinMode(PIN_BOTAO, INPUT_PULLUP);
  botaoRepousoAlto = true;
  return;
#elif defined(BOTAO_PRESSIONADO)
  // polaridade forcada pelo config.h
  botaoRepousoAlto = (BOTAO_PRESSIONADO == LOW);
  pinMode(PIN_BOTAO, botaoRepousoAlto ? INPUT_PULLUP : INPUT_PULLDOWN);
  Serial.println(botaoRepousoAlto ? "- Botao: polaridade forcada (aperta = LOW)" : "- Botao: polaridade forcada (aperta = HIGH)");
  return;
#else
  int comPullUp   = contaAltos(INPUT_PULLUP);
  int comPullDown = contaAltos(INPUT_PULLDOWN);
  if (comPullUp >= 18 && comPullDown >= 18) {
    // o proprio modulo puxa para HIGH em repouso: aperta = LOW
    botaoRepousoAlto = true;
    pinMode(PIN_BOTAO, INPUT);
    Serial.println("- Botao: repouso HIGH, aperta = LOW");
  } else if (comPullUp <= 2 && comPullDown <= 2) {
    // o proprio modulo puxa para LOW em repouso: aperta = HIGH
    botaoRepousoAlto = false;
    pinMode(PIN_BOTAO, INPUT);
    Serial.println("- Botao: repouso LOW, aperta = HIGH");
  } else {
    // o pino "flutua": o modulo nao tem resistor. Assume chave para GND, com resistor interno.
    botaoRepousoAlto = true;
    pinMode(PIN_BOTAO, INPUT_PULLUP);
    Serial.println("- Botao: AVISO, sem resistor no modulo; assumindo aperta = LOW (confira a ligacao)");
  }
#endif
}

// Roda na tarefaAtuadores a cada 2 ms. So considera um aperto (ou solta) depois de
// ~20 ms seguidos na mesma leitura, para ruido nao virar aperto.
// Nao grava na memoria aqui (gravar na flash pode atrasar os bipes): avisa o loop() por "mudoPendente".
void tratarBotao() {
  static bool confirmado = false;          // true = botao pressionado (ja confirmado)
  static uint8_t seguidas = 0;
  static unsigned long tUltimoAperto = 0;

  bool lidoPressionado = ((digitalRead(PIN_BOTAO) == HIGH) != botaoRepousoAlto);
  if (lidoPressionado == confirmado) {
    seguidas = 0;
    return;
  }
  if (++seguidas < 10) return;             // 10 leituras seguidas (~20 ms) diferentes do confirmado
  seguidas = 0;
  confirmado = lidoPressionado;

  Serial.println(confirmado ? "- Botao: pressionado" : "- Botao: solto");
  if (confirmado && millis() - tUltimoAperto > 300) {
    tUltimoAperto = millis();
    mudo = !mudo;
    mudoPendente = true;
    Serial.println(mudo ? "- Mute LIGADO" : "- Mute desligado");
  }
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
  // logo
  display.clearDisplay();
  display.drawBitmap((OLED_LARGURA - LOGO_W) / 2, 0, LOGO, LOGO_W, LOGO_H, SSD1306_WHITE);
  display.display();
  delay(1500);

  // boas-vindas (a setup() segura esta tela por mais 2 s)
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
  ledsApagados();
#if !SIMULACAO_WOKWI
  digitalWrite(PIN_BUZZER, BUZZER_ATIVO_EM_LOW ? HIGH : LOW);   // comeca em silencio
#endif
  detectaBotao();   // nao aperte o botao ao ligar o Node

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

  // botao, LED/buzzer e tela rodam por conta propria, independentes da rede
  xTaskCreatePinnedToCore(tarefaAtuadores, "atuad", 5120, NULL, 2, NULL, 1);
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

  // grava o mudo na memoria (o botao so marca "pendente", para nao atrasar os bipes)
  if (mudoPendente) {
    mudoPendente = false;
    prefs.putBool("mudo", mudo);
  }

  leSensores();
  if ((AVALIACAO_LOCAL_SEMPRE || offlineLocal) && !suspenso) avaliaLocal();
  publicaTelemetria();
  // tratarBotao(), atualizaAtuadores() e desenhaOled() rodam nas tarefas
}
