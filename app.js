import { config } from 'dotenv';
import { Logger } from './util/logger.mjs';
import { REST, Routes, Client, Collection, Events, GatewayIntentBits } from 'discord.js';
import { MongoClient, ServerApiVersion } from 'mongodb';
import * as commands from './commands/commands.js';

config();
const l = new Logger('log.txt', 'error.txt', false);

const uri = `mongodb+srv://${process.env.MONGO_USER}:${process.env.MONGO_PASSWD}@clusterdnd.qxfls1g.mongodb.net/?authSource=admin&retryWrites=true&w=majority&appName=ClusterDnD`;

// Create a MongoClient with a MongoClientOptions object to set the Stable API version
const mongo_client = new MongoClient(uri, {
    serverApi: {
        version: ServerApiVersion.v1,
        strict: true,
        deprecationErrors: true,
    }
});
l.log('[Mongo Connection] - Connection started');

const client = new Client({intents: [GatewayIntentBits.GuildMembers, GatewayIntentBits.Guilds], disableEveryone: false});

async function loadCommands()    {
    // Setting up the possible commands of the client
    client.commands = new Collection();
    const rest = new REST().setToken(process.env.DISCORD_TOKEN);

    for (const name in commands.default)   {
        const command = commands.default[name];
        client.commands.set(command.data.name, command);
        l.log('[INFO] - Deploying (/) commands');
        await rest.post(
            Routes.applicationCommands(process.env.APP_ID),
            {
                headers: {
                    'content-type':'application/json',
                    'Authorization':`Bot ${process.env.DISCORD_TOKEN}`,
                },
                body: command.data.toJSON(),
            },
        ).then(l.log(`[INFO] - Depoloyed (/) command ${name}`)).catch((err) => l.error(`[DEPLOY] - Error in deployment command ${name} - ${err}`));
        l.log('[INFO] - Deployed (/) commands');
    }
}

client.once(Events.ClientReady, readyClient => {
    l.log(`[INFO] - Logged in as ${readyClient.user.tag}`);
    loadCommands();
});
// FIXME: Don't know why but, when on prod server it crashes everything for an ECONNREFUSED unexplainable atm
client.once(Events.ClientReady, async c => {
    await mongo_client.connect();
    let ann = mongo_client.db(process.env.MONGO_DB_NAME).collection(process.env.MONGO_A_COLLECTION_NAME);
    let cursor = ann.find({});
    while (await cursor.hasNext()) {
        cursor.next().then(res => {
            l.info(`[INFO] - Addind listeners on ${res.guild}`);
            // Create event listener
            c.on(Events.GuildScheduledEventCreate, async (createdScheduledEventUrl) => {
                res.guild.scheduledEvents.fetch(createdScheduledEventUrl).then((scheduledEvent) => {
                    // Add id to fetch messages? Related to complexity doubts for update
                    res.channel.send(`Hey @everyone, è stata programmata una sessione! :eyes:\n"${scheduledEvent.name}"\nTenetevi pronti per ${new Intl.DateTimeFormat('it-IT', {weekday: 'long', day: 'numeric', month: 'long'}).format(scheduledEvent.scheduledStartAt)}! La sessione avrà inizio alle ore ${new Intl.DateTimeFormat('it-IT', {hour: 'numeric', minute: 'numeric'}).format(scheduledEvent.scheduledStartAt)}`);
                });
            });
            // Update event listenr
            c.on(Events.GuildScheduledEventUpdate, async (editedScheduledEventUrl) => {
                res.guild.scheduledEvents.fetch(editedScheduledEventUrl).then((oldScheduledEvent, newScheduledEvent) => {
                    res.channel.send(`Cambio di programmi @everyone! La sessione ${oldScheduledEvent.name} si terrà alle ore ${new Intl.DateTimeFormat('it-IT', {hour: 'numeric', minute: 'numeric'}).format(newScheduledEvent.scheduledStartAt)} di ${new Intl.DateTimeFormat('it-IT', {weekday: 'long', day: 'numeric', month: 'long'}).format(newScheduledEvent.scheduledStartAt)}`);
                });
            });
            // Delete event listenr
            c.on(Events.GuildScheduledEventDelete, async (deleteScheduledEventUrl) => {
                res.guild.scheduledEvents.fetch(deleteScheduledEventUrl).then((scheduledEvent) => {
                    res.channel.send(`@everyone, mi dispiace informarvi che la sessione ${scheduledEvent.name} è stata cancellata`);
                });
            });
            l.info(`[INFO] - Added listeners on ${res.guild}`);
        });
    }
    mongo_client.close();
})

// Listener that execute interactions
client.on(Events.InteractionCreate, async interaction => {
    if (!interaction.isChatInputCommand()) return;

    const command = await interaction.client.commands.get(interaction.commandName);

    if (!command)   {
        l.error(`[ERROR] - No command matching ${interaction.commandName} found`);
        return;
    }

    try {
        // Remember the typing, it's a ChatInputCommandInteraction
        await command.execute(interaction);
    } catch (error) {
        l.error(`[ERROR] - ${error}`);
        if (interaction.replied || interaction.deferred)    {
            await interaction.followUp({content: 'There was an error while executing this command!', ephemeral: true});
        }   else    {
            await interaction.reply({content: 'There was an error while executing this command!', ephemeral: true});
        }
    }
});

client.login(process.env.DISCORD_TOKEN);

export {mongo_client, client};