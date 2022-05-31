# Satosa-blockchainlab2SPID

- derivato da [Satosa-Saml2SPID](https://github.com/italia/Satosa-Saml2Spid)


la cartella [project](./project) è la copia della cartella [example](./example)

# Preparare Server

- creare un nuovo server ubuntu

- installare i seguenti pacchetti
 
    ```
    sudo apt-get update
    ```
    
    ```
    sudo apt-get install -y wget jq
    ```

- installare Docker e Docker-Compose
  
    ```
    sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

    ```
    ```
    sudo mkdir -p /etc/apt/keyrings

    ```
    ```
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    ```
    ```
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    ```
    ```
    sudo apt-get update
    ```
    ```
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

    ```    
    ```
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    ```
    ```
    mkdir -p $DOCKER_CONFIG/cli-plugins
    ```
    ```
    curl -SL https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose

    ```
    ```
    chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
    ```
    
# Scegliere Nomi di Dominio

ora bisogna scegliere due nomi di dominio e creare i relativi record DNS(entrambi dovranno puntare al server su cui stiamo installando il proxy), nel nostro caso:

-  spid.blockchainlab.it : riferito al servizio proxy basasto su satosa;
-  discovery.blockchainlab.it : riferito al servizio discovery e ai contenuti statici. 

Aggiornare i seguenti file con i nomi di dominio scelti e le informazioni personali richieste (Es. nome, contatti, p. iva...):

- [project/proxy_conf.yaml](./project/proxy_conf.yaml)
- [project/plugins/backends/saml2_backend.yaml](./project/plugins/backends/saml2_backend.yaml)
- [project/plugins/backends/spidsaml2_backend.yaml](./project/plugins/backends/spidsaml2_backend.yaml)
- [project/plugins/frontends/saml2_frontend.yaml](./project/plugins/frontends/saml2_frontend.yaml)

- [init-letsencrypt.sh](./init-letsencrypt.sh)
- [docker/gateway/satosa.conf](./docker/gateway/satosa.conf)

> NOTA per il file satosa.conf: <br>
> il nome della cartella in cui let's encrypt genera i certitificati per i due domini è il nome del primo dominio indicato nel file init-letsencrypt.sh, per entrambi i domini.

# Modificare Dockerfile
- [satosa-saml2spid](./docker/satosa-saml2spid/Dockerfile)

  commentare l'ultima linea
  ```
  #ENTRYPOINT uwsgi --wsgi satosa.wsgi --https 0.0.0.0:10000,/satosa_pki/cert.pem,/satosa_pki/privkey.pem --callable app -b 32648
  ```
  e sostituirla con
  ```
  ENTRYPOINT uwsgi --wsgi satosa.wsgi --http 0.0.0.0:10000 --callable app -b 32648
  ```
  
- [satosa-statics](./docker/satosa-statics/Dockerfile)

  commentare l'ultima linea
  ```
  #ENTRYPOINT uwsgi --uid 1000 --https 0.0.0.0:9999,/satosa_pki/cert.pem,/satosa_pki/privkey.pem --check-static-docroot --check-static $BASEDIR --static-index disco.html
  ```
  e sostituirla con
  ```
  ENTRYPOINT uwsgi --uid 1000 --http 0.0.0.0:9999 --check-static-docroot --check-static $BASEDIR --static-index disco.html
  
# Modificare i templates delle pagine statiche

modificare i seguenti file html:

- [project/static/disco.html](./project/static/disco.html)
- [project/static/error_page.html](./project/static/error_page.html)
- [project/templates/spid_base.html](./project/templates/spid_base.html)


# Aggiungere IdP 

- scaricare i metadata dell' Identity Provider che si vuole aggiungere nella cartella project/metadata/idp. Es.
    - [Validator di test](https://demo.spid.gov.it/validator/metadata.xml)
    - [ambiente Demo](https://demo.spid.gov.it/metadata.xml)

    ```
    wget https://demo.spid.gov.it/validator/metadata.xml -O Satosa-blockchainlab2SPID/project/metadata/idp/nome_idp.xml
    ```

- Aggiungere l' EntityID del Identity Provider al file [project/plugins/microservices/target_based_routing.yaml](./project/plugins/microservices/target_based_routing.yaml) seguendo lo stesso formato degli altri IdP già presenti.

- Aggiungere l'IdP al bottone 'Entra con SPID', aggiungendone l'entityID nel file [project/static/spid/spid-idps.js](./project/static/spid/spid-idps.js) seguendo lo stesso formato degli altri IdP già presenti.

# Aggiungere SP

> prima di scaricare i metadata bisogna [`creare una nuova connessione su Auth0`](#Auth0). 

- scaricare i metadata del Service Provider che si vuole aggiungere nella cartella project/metadata/sp

    ```
    wget https://con-cert.eu.auth0.com/samlp/metadata?connection=proxy -O Satosa-blockchainlab2SPID/project/metadata/sp/my-sp.xml
    ```

# DOCKER-COMPOSE

## - Modificare docker-compose.yaml

- inserire le informazioni necessarie per generare i certificati per il docker spid-certs;

  > nel campo *org-id* assicurarsi che la la partita iva o il codice fiscale siano inseriti rispettivamente secondo il seguente formato "VATIT-" o "CF:IT-".

- aggiungere il docker di nginx
    ```
    satosa-nginx:
        image: nginx:1.15-alpine
        container_name: satosa-nginx
        restart: unless-stopped
        volumes:
        - ./docker/gateway/satosa.conf:/etc/nginx/conf.d/default.conf
        - satosa-saml2saml_statics:/satosa_statics
        - ./docker/gateway/log:/var/log/nginx
        - ./docker/certbot/conf:/etc/letsencrypt
        - ./docker/certbot/www:/var/www/certbot
        ports:
        - "80:80"
        - "443:443"
        command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \"daemon off;\"'"
        networks:
        - satosa
    ```
- aggiungere il docker di certbot per generare i certificati SSL per let's encrypt
    ```
    certbot:
        image: certbot/certbot
        container_name: certbot
        restart: unless-stopped
        volumes:
        - ./docker/certbot/conf:/etc/letsencrypt
        - ./docker/certbot/www:/var/www/certbot
        entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    ```

## Eseguire Satosa

Creare i volumi
```
docker volume create --name=satosa-saml2saml_certs
```
```
docker volume create --name=satosa-saml2saml_conf
```
```
docker volume create --name=satosa-saml2saml_statics
```
```
docker volume create --name=satosa-saml2saml_logs
```

Copiare i file nei volumi di destinazione

```
cp project/pki/*pem `docker volume inspect satosa-saml2saml_certs | jq .[0].Mountpoint | sed 's/"//g'`
```
```
cp -R project/* `docker volume inspect satosa-saml2saml_conf | jq .[0].Mountpoint | sed 's/"//g'`
```
```
cp -R project/static/* `docker volume inspect satosa-saml2saml_statics | jq .[0].Mountpoint | sed 's/"//g'`
```

se è il primo avvio eseguite:
```
./init-letsencrypt.sh
```
in questo modo verranno creati i certificati per HTTPS.

altrimenti avviare docker-compose
```
docker-compose up -d
```

See [mongo readme](./mongo/README.md) to have some example of demo data.


# Metadata Proxy

- Metadata frontend (da fornire al SP)

        https://spid.blockchainlab.it/Saml2IDP/metadata
- Metadata backend (da fornire all' IdP)

        https://spid.blockchainlab.it/spidSaml2/metadata
# Auth0

- Creare una nuova connessione in Authentication>Enterprise>SAML.
    
    **Sign in URL**:
            
        https://spid.blockchainlab.it/Saml2/sso/post

    o cercare _md:SingleSignOnService_ nei metadata del frontend;

    **X509 Signing Certificate**:

    Ottenerlo dai metadata del frontend.
    
    > NOTA:
    > se stai creando la connessione su Auth0 prima di aver eseguito satosa, puoi utilizzare un certificato qualsiasi (ad esempio quello che trovi nella cartella [pki](./example/pki). 
    
    >RICORDA PERO' DI MODIFICARLO CON QUELLO CONTENUTO NEI METADATA DOPO CHE AVRAI ESEGUITO SATOSA!!

# Aggiornare Signing Keys per la connessione appena creata
Ottenere Acceess Token per l' applicazione 'API Exploreer Application'.

````
curl --request POST \
  --url https://con-cert.eu.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{"client_id":"<client_id>","client_secret":"<client_secreet>","audience":"https://con-cert.eu.auth0.com/api/v2/","grant_type":"client_credentials"}'
````
utilizzabile poi con client come Postman o da command line con curl:
````
curl --request GET \
  --url http://path_to_your_api/ \
  --header 'authorization: Bearer <access_token>
````

## API da utilizzare:

- GET https://con-cert.eu.auth0.com/api/v2/connections

    restituisce tutte le informazioni di tutte le connessioni create

- GET https://con-cert.eu.auth0.com/api/v2/connections/_connection_id_

    restituisce tutte le informazioni di quella specifica connessione

- PATCH https://con-cert.eu.auth0.com/api/v2/connections/_connection_id_

    sovrascrive le informazioni della connessione con quelle inserite nel body della richiesta. qui vanno inserite le chiavi.


# Creare mapping attributi nella connessione Auth0

Authentication > Enterprise > SAML > _nome_connessione_ > Mappings
````
{
  "sn": "urn:oid:2.5.4.4",
  "name": "Name",
  "email": "urn:oid:1.2.840.113549.1.9.1.1",
  "spid_code": "spidCode",
  "given_name": "urn:oid:2.5.4.42",
  "family_name": "familyName",
  "display_name": "urn:oid:2.16.840.1.113730.3.1.241",
  "eduPersonTargetedID": "urn:oid:1.3.6.1.4.1.5923.1.1.1.10"
}
````

# Abilitare connessione in un'Applicazione e testarla

prima di testare controllare che l' url del sito di origine sia inserito tra i siti autorizzati all' interno dell' Applicazione dentro la quale è stata abilitata la connessione e ricordarsi di scaricare i metadata del nostro backend sulla pagina dell'ambiente validator.

# Diventare Fornitore di Servizi SPID

Per essere abilitat come Service Provider bisogna seguire una [procedura tecnica](https://www.spid.gov.it/cos-e-spid/diventa-fornitore-di-servizi/procedura-tecnica/) ed in caso il proxy superi le verifiche effettuate da AgID, una [procedura amministrativa](https://www.spid.gov.it/cos-e-spid/diventa-fornitore-di-servizi/procedura-amministrativa/).
