Build and run locally
=====================

```
docker build --tag stormbot .
docker run -i -t --device /dev/snd -e AUDIODEV=hw:1,0 -v /var/cache/stormbot/:/var/cache/stormbot/ -v ~/Music:/app/Music/ stormbot stormbot --jid $jid $room --plugins stormbot_fortune.fortune,stormbot_music.music,stormbot_quote.quote,stormbot_quizz.quizz,stormbot_say.say --music-player play --music-path Music/ --music-default $music_default
```
