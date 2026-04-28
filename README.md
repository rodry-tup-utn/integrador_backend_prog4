# Entrega parcial 1 - link al video

[Link a la carpeta del video](https://drive.google.com/drive/folders/1kaCuwf9_A2KVDeiCYk1yYTer775apSkW?usp=sharing)

# 📦 API Backend - Programación IV

Proyecto desarrollado para la materia **Programación IV**  
Carrera: Tecnicatura Universitaria en Programación - UTN FRM

👨‍💻 Alumnos:

- Leandro Mercado
- Rodrigo Ramirez

---

## 🚀 Descripción

API backend desarrollada con **FastAPI + SQLModel + PostgreSQL** para la gestión de productos, categorías e ingredientes.

El objetivo es implementar un sistema con relaciones entre entidades y exponer endpoints funcionales siguiendo buenas prácticas.

---

## 🧱 Módulos implementados

- Categoría
- Producto
- Ingrediente
- ProductoCategoria
- ProductoIngrediente

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

## 🎥 Video demostración

👉 _(Agregar link aquí)_

---

## ⚙️ Tecnologías

- FastAPI
- SQLModel
- PostgreSQL
- Docker

---
