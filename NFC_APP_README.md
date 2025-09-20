# Guía de Implementación NFC - Aplicación Android (Kotlin)

Documentación técnica para desarrolladores de la aplicación Android en Kotlin que implementará el sistema de marcaje por NFC.

## Resumen del Sistema

La aplicación Android debe leer tokens JWT almacenados en chips **NTAG215** y enviarlos a la API para registrar entrada y salida de empleados. El sistema utiliza autenticación por tokens JWT firmados con clave secreta del servidor.

## Arquitectura de Datos

### Token NFC (NTAG215)
Cada empleado tiene un chip NTAG215 que contiene un **token JWT completo**:

```
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbXBsb3llZV9pZCI6MiwidGFnX2lkIjoibmZjX3RhZ18xMjM0NSIsImV4cCI6MTczNTY4OTEyMCwiaWF0IjoxNzA0MTUzMTIwfQ.SIGNATURE_GENERADA_CON_SECRET_KEY
```

**Contenido decodificado del JWT:**
```json
{
  "employee_id": 2,
  "tag_id": "nfc_tag_12345", 
  "exp": 1735689120,
  "iat": 1704153120
}
```

### Características del Token
- **Formato**: JWT firmado con HMAC SHA-256
- **Tamaño máximo**: 504 bytes (compatible con NTAG215)
- **Validez**: 1 año desde la creación
- **Seguridad**: Firmado con SECRET_KEY del servidor (imposible de falsificar)

## Funcionalidad de la App Android

### 1. Configuración de Permisos Android

Agregar al `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.NFC" />
<uses-feature android:name="android.hardware.nfc" android:required="true" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

### 2. Lectura de NFC

La app debe usar las APIs nativas de Android (`NfcAdapter`, `Ndef`) para leer el token completo del chip NTAG215 sin procesarlo ni modificarlo.

### 3. Endpoints de la API

#### Marcaje de Entrada
```
POST /v1/attendance/in/
Content-Type: application/json

{
  "method": "nfc",
  "token": "token_jwt_completo_leido_del_chip"
}
```

**Respuesta exitosa (201):**
```json
[
  {"message": "Entrada registrada exitosamente para juan"},
  {"employee_name": "Juan Médico"}
]
```

#### Marcaje de Salida
```
POST /v1/attendance/out/
Content-Type: application/json

{
  "method": "nfc",
  "token": "token_jwt_completo_leido_del_chip"
}
```

**Respuesta exitosa (201):**
```json
[
  {"message": "Salida registrada exitosamente para juan"},
  {"employee_name": "Juan Médico"}
]
```

### 4. Errores Comunes
- `"Token NFC es requerido"` (400)
- `"Token NFC inválido o revocado"` (400)
- `"Empleado no encontrado"` (404)
- `"No hay registro de entrada pendiente"` (400) - Solo en salida

## Implementación Sugerida

### Dependencias Necesarias
- Retrofit para llamadas HTTP
- Corrutinas de Kotlin para operaciones asíncronas
- APIs nativas de Android NFC (`NfcAdapter`, `Ndef`)

### Flujo General
1. **Configurar NFC** - Detectar tags y leer contenido
2. **Extraer token** - Obtener el JWT completo del chip
3. **Enviar a API** - POST al endpoint correspondiente (entrada/salida)
4. **Mostrar resultado** - Confirmación o mensaje de error

## Consideraciones de Seguridad

### Lo que SÍ maneja la app:
- ✅ Lectura del token JWT completo del chip NFC
- ✅ Envío del token sin modificaciones a la API
- ✅ Manejo de respuestas y errores de la API
- ✅ Validación de conectividad antes de enviar

### Lo que NO maneja la app:
- ❌ **No** intentes decodificar o validar el JWT localmente
- ❌ **No** manejes la SECRET_KEY (solo el servidor la conoce)
- ❌ **No** modifiques el contenido del token leído
- ❌ **No** almacenes tokens en la app (siempre lee del chip)

## Configuración de la App

### Manejo de NFC
- Configurar `NfcAdapter` para detectar tags NTAG215
- Implementar `onNewIntent()` para manejar eventos NFC
- Validar disponibilidad de hardware NFC

### Manejo de Errores
- Validar conectividad antes de enviar requests
- Mostrar mensajes de error apropiados al usuario
- Implementar retry logic para fallos de red

## Validación Opcional de Token

Si necesitas validar un token sin registrar asistencia:

#### Endpoint
```
POST /v1/auth/nfc/validate/
Content-Type: application/json
```

#### Request
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Response (Éxito)
```json
{
  "employee_id": 2,
  "tag_id": "nfc_tag_12345",
  "exp": 1735689120,
  "iat": 1704153120
}
```

## Notas Técnicas

### Compatibilidad NFC
- **Chip requerido**: NTAG215 (504 bytes disponibles)
- **Protocolo**: ISO 14443 Type A
- **Frecuencia**: 13.56 MHz

### Consideraciones de Rendimiento
- **Cache de conectividad**: Verificar conexión antes de intentar marcaje
- **Retry logic**: Reintentar automáticamente en caso de falla de red
- **Feedback visual**: Mostrar estado de lectura NFC y envío a API

### Testing
- Probar con tokens válidos e inválidos
- Simular errores de red y NFC
- Validar comportamiento con chips vacíos o corruptos
- Verificar manejo correcto de respuestas de la API

## Flujo Visual Sugerido

```
1. [Pantalla Inicial] 
   → "Acerca tu chip NFC"

2. [Leyendo NFC]
   → Spinner + "Leyendo chip..."

3. [Enviando a API]
   → Spinner + "Registrando asistencia..."

4. [Resultado]
   → ✅ "Entrada registrada - Juan Médico"
   → ❌ "Error: Token inválido"
```

Esta guía cubre todo lo necesario para implementar la funcionalidad NFC en tu aplicación móvil de forma segura y eficiente.