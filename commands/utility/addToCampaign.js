import { SlashCommandBuilder } from "discord.js";
import { mongo_client } from "../../app.js";

// Template of objects:
// interface User look up https://discord.js.org/docs/packages/discord.js/14.14.1/User:Class
// interface Campaign {
//     _id:ObjectId,
//     name: string,
//     elements: {
//         dm: User,
//         players: Array<User>
//     }
// }
const locales = {
    it: {
        'user_added': 'L\'utente è stato inserito nella campagna',
    }
};
export default {
    'data': new SlashCommandBuilder()
        .setName('add')
        .setNameLocalizations({
            it:'aggiungi',
        })
        .setDescription('Add a user to your campaign')
        .setDescriptionLocalizations({
            it:'Aggiungi un utente alla tua campagna',
        })
        .addStringOption(option => {
            return option.setName('name')
            .setNameLocalizations({
                it:'nome',
            })
            .setDescription('Name of your campaign')
            .setDescriptionLocalizations({
                it:'Nome della tua campagna',
            })
            .setRequired(true);
        })
        .addUserOption(option => {
            return option.setName('user')
            .setNameLocalizations({
                it:'utente',
            })
            .setDescription('User to add')
            .setDescriptionLocalizations({
                it:'Utente da aggiungere',
            })
            .setRequired(true);
        }),
        async execute(interaction) {
            interaction.deferReply();
            await mongo_client.connect();
            let campaigns = mongo_client.db(process.env.MONGO_DB_NAME).collection(process.env.MONGO_COLLECTION_NAME);
            let c_n = interaction.options.get('name');
            console.log('[INFO] - Trying to add a user to a campaign');
            let re = await campaigns.findOne({name:c_n}, async (err, result) => {
                console.log('Finding a campaign');
                if (err) throw err;
                
                if (result) {
                    let n = result;
                    n['elements']['players'].push(interaction.options.get('user'));
                    // TODO: Setup the roles properly
                    await campaigns.updateOne({name:cn}, n);
                    interaction.editReply({
                        content: locales[interaction.locale]['user_added'] ?? 'User was added to the campaign',
                        ephemeral: false,
                    });
                }
                console.log('End of async');
            });
            console.log(re);
            console.log(campaigns);
            console.log('[INFO] - A user was added to a campaign');
        }
};