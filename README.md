# iotabot

A personal project that I'm currently working on. I know this is quite a mess, I'll keep updating it until I feel
satisfied with the code. 

Will also be adding new features besides osu! tracking.

# Running
1. PostgreSQL database with PostgreSQL 9.5 or higher

Create three tables with the following column names:
```
CREATE TABLE track (
 guild_id TYPE bigint,
 channel_id TYPE bigint,
 user_id TYPE bigint,
 username TYPE character varying,
 pp_raw TYPE double precision,
 accuracy TYPE double precision,
 pp_rank TYPE bigint,
 pp_country_rank TYPE bigint,
 country TYPE character varying
) ;
```
```
CREATE TABLE top_scores (
 user_id TYPE bigint,
 username TYPE character varying,
 scores TYPE character varying
 ) ;
 ```
 ```
 CREATE TABLE latest_score (
 user_id TYPE bigint,
 username TYPE character varying,
 discord_user_id TYPE bigint,
 pp_rank TYPE bigint
) ;
```
2. Setup configuration
Create a vars.env file in the root directory where launcher.py is with this template:
```
osu_token='' # your osu! api token
discord_token='' # your discord api token
login='' # your PostgreSQL login
passw='' # your PostgreSQL password
db='' # your PostgreSQL database name
```
