#  Sistema Experto en Hardware 

Un sistema experto capaz de recomendar configuraciones de PC según:

-   Perfil del usuario (gamer, diseñador, programador, estudiante,
    ofimático)
-   Presupuesto en moneda local (MXN)
-   Tipo de equipo (PC de escritorio o laptop)
-   Reglas de negocio basadas en ingeniería de requerimientos
-   Base de conocimiento modular y ampliable en JSON

Implementado con:

-   🚀 **FastAPI** (backend)
-   🎨 **Tkinter** (interfaz gráfica)
-   🔧 **Motor de reglas propio**
-   📚 **Base de conocimiento estructurada**
-   📊 **Visualización de distribución presupuestal**

## Estructura del proyecto

LATEST SISTEMA HARDWARE/ │ ├── api/ │ └── main.py\
├── engine/ │ ├── inference/ │ ├── rules/ │ └── utils/ ├── ui/ │ └──
app_ui.py ├── base_knowledge.json └── README.md

## 🛠 Instalación

### 1) Clonar repositorio

git clone https://github.com/Masherzn/sistema-experto-hardware.git


### 4) Instalar dependencias

pip install -r requirements.txt

##  Ejecutar backend

uvicorn api.main:app --reload

##  Ejecutar interfaz gráfica

python ui/app_ui.py
