.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Disable Company in PriceList
=============================

Este módulo deastiva el campo compañia en las tarifas para que todas las tarifas esten disponibles en todas las compañias.


Installation
============

* product

Configuration
=============

1. Este modulo requiere la instalación de el moduli product

Usage
=======
Este modulo lo que realmente hace es que hace invisible el campo compañia en tarifas, asi mismo hace que por defecto este
campo en tarifas este vacio.
Asi mismo este modulo se engancha a las funciones de creacion y escritura de tarifas, para que en caso de que el campo 
compañia se intentara escribir con un valor no vacio, que se modfique esto y se quede vacio.
La razon de esto es para permitir que todas las tarifas se puedan usar en todas las compañias.
Esto es asi porque este modulo es para empresas que usan multicompañia y tienen una tarifa por cliente pero todas sus
compañias comparten clientes, por lo que necesitan que las tarifas de estos clientes esten disponibles para ser usadas
en ambas compañias sin mayor complicacion.

Credits
=======

Contributors
------------

* Aitor Rosell Torralba <arosell@praxya.es>

Maintainer
----------

.. image:: http://praxya.com/wp-content/uploads/2015/11/logo-h-nomargin.jpg
   :alt: Praxya
   :target: http://www.praxya.com/

This module is maintained by Praxya.
