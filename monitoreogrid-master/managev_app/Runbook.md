## Allow remote access to mysql db on ubuntu server

Instrucciones detalladas:
- https://www.digitalocean.com/community/tutorials/how-to-allow-remote-access-to-mysql

Para la configuración necesitamos un hostname, se saca intentándose conectar desde python mysq:
```
mysql.connector.connect(
                user="admin",
                password="actuadores",
                host="104.236.94.94",
                database="monitoreodb",
            )
```
Obtendremos un output como el siguiene:
```
mysql.connector.errors.DatabaseError: 1130: Host '179.14.141.215' is not allowed to connect to this MySQL server

```
De allí extraemos el hostmane. En este caso 179.14.141.215
La red no puede ser la de eafit, debe ser una red doméstica

- Entramos al servidor con putty:

![image](https://user-images.githubusercontent.com/37352122/139784925-99fe37e6-cfe3-4931-8d01-ac60bc84d1b0.png)

Luego ejecutamos los siguientes comandos:
```
sudo mysql
create user  'admin'@'179.14.141.215' identified by 'actuadores';
grant all on monitoreodb.* to 'admin'@'179.14.141.215';
 GRANT CREATE, ALTER, DROP, INSERT, UPDATE, DELETE, SELECT, REFERENCES, RELOAD on *.* TO 'admin'@'179.14.141.215' WITH GRANT OPTION;
exit
sudo ufw allow from 179.14.141.215 port 3306
```
Finalente, configuramos mysql para conectarse a la base de datos remota:

![image](https://user-images.githubusercontent.com/37352122/139785496-d070dc6e-c4b8-4b7a-8e80-38ac89445d66.png)


## Como desplegar ManagEV en tu máquina local

1) Clonar el repositorio
2) Instalaste requirements.txt
3) Descargar la aplicación MYSQL
4) Abrir mysql Shell
5) Crear usuario en mysql:
      usuario: admin@localhost
      password: 5Actu_adores.
6) Crear la base de datos llamada monitoreodb
7) Luego se debe ejecutar en la terminal de la carpeta clonada
      flask db migrate
      flask db upgrade
      
En caso que aparezca que el usuario no tiene permisos sobre la tabla monitoreodb, se debe acceder a mysql shell con el usuario administrador y darle todos los permisos al usuario creado sobre las tablas con "GRANT....."
