# iotabot

A personal project that I'm currently working on. I'll keep updating it until I feel
satisfied with the code and it's features. 

# Running
1. PostgreSQL database with PostgreSQL 9.5 or higher

Create three tables with the following column names:
```
CREATE TABLE track (
 guild_id bigint,
 channel_id bigint,
 user_id bigint,
 username character varying,
 pp_raw double precision,
 accuracy double precision,
 pp_rank bigint,
 pp_country_rank bigint,
 country character varying
) ;
```
```
CREATE TABLE top_scores (
 user_id bigint,
 username character varying,
 scores character varying
 ) ;
 ```
 ```
 CREATE TABLE latest_score (
 user_id bigint,
 username character varying,
 discord_user_id bigint,
 pp_rank bigint
) ;
```
2. Setup configuration

Create a vars.env file in the root directory where launcher.py is with this template:
```
osu_token='' # your osu! api token
discord_token='' # your discord api token
db='' # your PostgreSQL database name
login='' # your PostgreSQL database login
passw='' # your PostgreSQL database password
command_prefix='' # your bot command prefix symbol
```
