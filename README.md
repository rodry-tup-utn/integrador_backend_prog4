# 📦 API Backend - Programación IV

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.22-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-compose-blue?logo=docker)

Proyecto desarrollado para la materia **Programación IV**  
Carrera: Tecnicatura Universitaria en Programación - UTN FRM

---
## Link a video final https://drive.google.com/drive/folders/1ba81BAq61iIyDVPwluYpGlM2iw8nLIxT?usp=drive_link

---
## 🚀 Descripción

API backend desarrollada con **FastAPI + SQLModel + PostgreSQL** para la gestión de productos, categorías, ingredientes, pedidos, pagos y usuarios.

---

## 🧱 Módulos implementados

- Categoría
- Producto
- Ingrediente
- ProductoCategoria
- ProductoIngrediente
- Auth / Usuario
- Pedido / Order / OrderItem
- Pagos
- Estadísticas
- WebSocket

---

## 🗄️ Modelado de Datos

Se utilizó **SQLModel** para definir las entidades y sus relaciones.

- Relaciones implementadas con:
  - `Relationship`
  - `back_populates`

- Tipos de relaciones:
  - Uno a muchos (1:N)
  - Muchos a muchos (N:M) mediante tablas intermedias

---

## 🔌 Endpoints y Lógica

- Uso de:
  - `Annotated`
  - `Query` (para filtros y validaciones)

- Manejo de errores:
  - `HTTPException`
  - Códigos de estado HTTP adecuados

---

## 🐘 Persistencia

- Base de datos: PostgreSQL
- Conexión mediante Docker

---

## 🌐 Deploy

- **App:** [https://food-store-backend-31ki.onrender.com/](https://food-store-backend-31ki.onrender.com/)
- **Documentación (Swagger):** [https://food-store-backend-31ki.onrender.com/docs](https://food-store-backend-31ki.onrender.com/docs)

---

## 📁 Estructura del proyecto

```
server/
├── app/
│   ├── core/           # Configuración, dependencias
│   ├── db/             # Conexión y sesión de base de datos
│   ├── modules/        # auth, category, product, order, etc.
│   ├── test/           # Tests
│   └── main.py         # Entry point
├── .env.example
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## ⚙️ Tecnologías

- FastAPI
- SQLModel
- PostgreSQL
- Docker

---

## 🚀 Quick Start

```bash
git clone <repo>
cp .env.example .env
# editar .env con tus credenciales

make init   # crea venv, instala dependencias y levanta docker
make run    # uvicorn app.main:app --reload
make down   # detiene docker compose
```

---

## 📹 Videos de entregas

### Entrega parcial 1

[Link a la carpeta del video](https://drive.google.com/drive/folders/1kaCuwf9_A2KVDeiCYk1yYTer775apSkW?usp=sharing)

### Entrega parcial 2

[Link a la carpeta del video](https://drive.google.com/drive/folders/1Wnf7Lnq5ItKVFPtEi0c9EeA6X1bq7FrO?usp=drive_link)

---

## 👨‍💻 Alumnos

- Leandro Mercado
- Rodrigo Ramirez
