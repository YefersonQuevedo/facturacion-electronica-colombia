# 🧾 Proyecto: Facturación Electrónica Colombia 🇨🇴

Este proyecto es una **API web desarrollada en Python con FastAPI**, diseñada para enviar **facturas electrónicas, notas crédito** y próximamente **notas débito** a la DIAN en Colombia.

Actualmente se encuentra funcionando en ambiente de **habilitación**.

🎥 Video explicativo en YouTube:  
👉 [Facturación electrónica DIAN COLOMBIA software propio - API GRATIS](https://youtu.be/EaDoYikq-DI?si=W-lIRWI1gwBewll2)

📞 ¿Necesitas ayuda técnica o soporte?  
Puedes contactarme por WhatsApp: **+57 300 812 0524**

---

## 📦 Instalación

### 1. 🔽 Requisitos previos  
Instala **Python 3.10** o **3.11** desde el sitio oficial:  
👉 [https://www.python.org/downloads/release/python-3100/](https://www.python.org/downloads/release/python-3100/)  
✅ Marca la opción **“Add Python to PATH”** durante la instalación.

---

### 2. 🧰 Clona el repositorio y accede al proyecto
```bash
git clone https://github.com/Crispancho93/facturacion-electronica-colombia.git
cd facturacion-electronica-colombia
3. 🧪 Crea y activa un entorno virtual
En Windows:
bash
Copiar
Editar
py -3.10 -m venv venv310     # o py -3.11 -m venv venv311
venv310\Scripts\activate
En Linux/macOS:
bash
Copiar
Editar
python3.10 -m venv venv310   # o python3.11 -m venv venv311
source venv310/bin/activate
4. 📦 Instala las dependencias
bash
Copiar
Editar
pip install -r requirements.txt
✅ Esto instalará correctamente lxml==4.8.0 y demás paquetes compatibles con Python 3.10 o 3.11 en Windows.

5. 🚀 Ejecuta el servidor de desarrollo
bash
Copiar
Editar
uvicorn app:app --reload
Luego abre tu navegador en:
👉 http://localhost:8000/docs

Ahí encontrarás la documentación interactiva de la API.

🧪 Probar con Postman
Puedes enviar facturas fácilmente desde Postman:

Método: POST

URL: http://127.0.0.1:8000/api/invoice/create_invoice

Body: selecciona raw → application/json

Contenido: pega el JSON correspondiente a tu factura

📁 Estructura del Proyecto
csharp
Copiar
Editar
facturacion-electronica-colombia/
│
├── app/                    # Lógica principal del proyecto
│   ├── routes/             # Endpoints de la API
│   ├── services/           # Lógica de negocio
│   └── models/             # Esquemas y validaciones
│
├── static/                 # Archivos estáticos (si aplica)
├── templates/              # Plantillas HTML (si aplica)
├── main.py                 # Punto de entrada alternativo
├── requirements.txt        # Dependencias del proyecto
└── README.md               # Documentación
📌 Pendiente por validar
 Validar el campo IndustryClasificationCode (Código de actividad económica registrado en el RUT)

🤝 Contribución
¿Quieres colaborar? ¡Genial! Sigue estos pasos:

Haz un fork del repositorio.

Crea una rama nueva:

bash
Copiar
Editar
git checkout -b feature/nueva-caracteristica
Realiza tus cambios y haz commit:

bash
Copiar
Editar
git commit -am "Agrega nueva característica"
Haz push a tu rama:

bash
Copiar
Editar
git push origin feature/nueva-caracteristica
Abre un Pull Request 🚀

⚖️ Licencia
Este proyecto está licenciado bajo la Licencia GPLv2, igual que el kernel de Linux.
Puedes usar, modificar y distribuir el software respetando los términos de dicha licencia.