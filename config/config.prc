# Internal
dc-file config/dclass/cars.dc
dc-file config/dclass/otp.dc

mongodb-host mongodb://127.0.0.1:27017
mongodb-name woc

default-directnotify-level info

# Population Levels (for ShardManager):
# (NONE, VERY_LIGHT, LIGHT, MEDIUM, FULL, VERY_FULL)
shard-population-levels [0, 1, 50, 100, 150, 200]
