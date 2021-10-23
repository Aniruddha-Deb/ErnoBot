# ErnoBot

Companion discord bot for the RubiksCube quiz system

## Instructions

- Setup a discord server with the channel names `team-x`, where `x` is 1-indexed team ID, and `quizmaster`.
- Make a bot, and give it permissions to all these channels and the quizmaster channel
- Initialize the bot with your token in the .env file (template:)
```
SECRET_KEY='x'
BOT_TOKEN='xx'
```
(where secret key is shared with your flask app)
- Run the bot _after_ running the server 
- Have fun! `qp` to pounce, `qtc` to create teams, and `qpurge` if you want to clear some chats. Pounce open/close is handled from the frontend, so no need to worry about that.