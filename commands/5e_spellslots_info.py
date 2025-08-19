import logging
import traceback
import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands
from math import floor

locales = {
    "it":   {
        "ask_for_classes": "Mi potresti dire le classi del tuo pg? Per favore, segui la seguente leggenda",
        "ask_for_class": "Mi potresti dire la classe del tuo pg?",
        "legend": "class:level\nE.g.:\n'warlock:1, cleric:2, wizard:6'",
        "level_text": "livello",
        "repsonse_intro": "Hai i seguenti slot incantesimo",
        "generic_error": "Si è verificato un errore",
        "timeout_error": "Ti ho dato due minuti, eh. Devi fare più in fretta :)",
        "format_error": "No, zì, non sto a capì niente. Per favore, riprova il comando e segui la formattazione :)",
    },
    "eng":  {
        "ask_for_classes": "Can you give me the classes of your pg? Please, refer to the following legend",
        "ask_for_class": "Can you give me the class of your pg?",
        "legend": "class:level\nE.g.:\n'warlock:1, cleric:2, wizard:6'",
        "level_text": "level",
        "repsonse_intro": "Your spell slots are",
        "generic_error": "An error has occurred",
        "timeout_error": "Time out while waiting for your message",
        "format_error": "Format error, please, try again",
    }
}

class SpellSlotInfo(commands.Cog):
    __MATRIX_MC_SPELL_SLOT = [
        [2,0,0,0,0,0,0,0,0],
        [3,0,0,0,0,0,0,0,0],
        [4,2,0,0,0,0,0,0,0],
        [4,3,0,0,0,0,0,0,0],
        [4,3,2,0,0,0,0,0,0],
        [4,3,3,0,0,0,0,0,0],
        [4,3,3,1,0,0,0,0,0],
        [4,3,3,2,0,0,0,0,0],
        [4,3,3,3,1,0,0,0,0],
        [4,3,3,3,2,0,0,0,0],
        [4,3,3,3,2,1,0,0,0],
        [4,3,3,3,2,1,0,0,0],
        [4,3,3,3,2,1,1,0,0],
        [4,3,3,3,2,1,1,0,0],
        [4,3,3,3,2,1,1,1,0],
        [4,3,3,3,2,1,1,1,0],
        [4,3,3,3,2,1,1,1,1],
        [4,3,3,3,3,1,1,1,1],
        [4,3,3,3,3,2,1,1,1],
        [4,3,3,3,3,2,2,1,1],
    ]
    class FormatError(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    
    class PGBuilder:
        class PG:
            def __init__(self):
                self.barbarian = 0
                self.bard = 0
                self.cleric = 0
                self.druid = 0
                self.fighter = 0
                self.monk = 0
                self.paladin = 0
                self.ranger = 0
                self.rogue = 0
                self.sorcerer = 0
                self.warlock = 0
                self.wizard = 0

            def add_level(self, cls: str, level: int) -> None:
                if cls == "barbarian":
                    self.barbarian = int(level)
                if cls == "bard":
                    self.bard = int(level)
                if cls == "cleric":
                    self.cleric = int(level)
                if cls == "druid":
                    self.druid = int(level)
                if cls == "fighter":
                    self.fighter = int(level)
                if cls == "monk":
                    self.monk = int(level)
                if cls == "paladin":
                    self.paladin = int(level)
                if cls == "ranger":
                    self.ranger = int(level)
                if cls == "rogue":
                    self.rogue = int(level)
                if cls == "sorcerer":
                    self.sorcerer = int(level)
                if cls == "warlock":
                    self.warlock = int(level)
                if cls == "wizard":
                    self.wizard = int(level)

            def get_enchanter_level(self) -> int:
                # bard + cleric + druid + sorcerer + wizzard + ⌊paladin/2⌋ + ⌊ranger/2⌋ + ⌊fighter/3⌋ + ⌊rogue/3⌋
                return (
                    self.bard +
                    self.cleric +
                    self.druid +
                    floor(self.fighter / 3) +
                    floor(self.paladin / 2) +
                    floor(self.ranger / 2) +
                    floor(self.rogue / 3) +
                    self.sorcerer +
                    floor(self.warlock / 2) +
                    self.wizard
                )

            def __getitem__(self, key: str|int) -> int:
                if type(key) != str or type(key) != int:
                    raise TypeError
                if key > 11:
                    raise IndexError
                
                if (type(key) == str and key == "barbarian") or key == 0:
                    return self.barbarian
                if (type(key) == str and key == "bard") or key == 1:
                    return self.bard
                if (type(key) == str and key == "cleric") or key == 2:
                    return self.cleric
                if (type(key) == str and key == "druid") or key == 3:
                    return self.druid
                if (type(key) == str and key == "fighter") or key == 4:
                    return self.fighter
                if (type(key) == str and key == "monk") or key == 5:
                    return self.monk
                if (type(key) == str and key == "paladin") or key == 6:
                    return self.paladin
                if (type(key) == str and key == "ranger") or key == 7:
                    return self.ranger
                if (type(key) == str and key == "rogue") or key == 8:
                    return self.rogue
                if (type(key) == str and key == "sorcerer") or key == 9:
                    return self.sorcerer
                if (type(key) == str and key == "warlock") or key == 10:
                    return self.warlock
                if (type(key) == str and key == "wizard") or key == 11:
                    return self.wizard
                
                raise KeyError

        @classmethod
        def parse(cls, m: str) -> 'SpellSlotInfo.PGBuilder.PG':
            p = cls.PG()
            m = m.strip().lower().replace(" ", "").split(",")
            for c in m:
                try:
                    cl, l = c.split(":")[0], c.split(':')[1]
                    p.add_level(cl, l)
                except Exception:
                    raise SpellSlotInfo.FormatError("Invalid format")
            return p
        @classmethod
        def single_parse(cls, m: str, l: int) -> 'SpellSlotInfo.PGBuilder.PG':
            p = cls.PG()
            m = m.strip().lower().replace(" ", "").split(",")[0]
            try:
                p.add_level(m, l)
            except Exception:
                raise SpellSlotInfo.FormatError("Invalid format")
            return p

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Define the group
    spell_info_group = app_commands.Group(
        name="5e_info",
        description="Info useful for 5th edition"
    )

    # Subcommand
    @spell_info_group.command(
        name="spell_slots_info",
        description="Get how many spell slots your pg has"
    )
    @app_commands.describe(pg_level="Level of your PG", multiclass="If your pg has multiclassed")
    async def spell_slots_info(
        self,
        interaction: discord.Interaction,
        pg_level: int,
        multiclass: Optional[bool] = False
    ):
        locale = interaction.locale if interaction.locale in locales else "eng"
        await interaction.response.defer()
        
        try:
            if multiclass:
                await interaction.followup.send(f"{locales[locale]['ask_for_classes']} - {locales[locale]['legend']}")
                msg = await interaction.client.wait_for('message', timeout=120)
                pg = self.PGBuilder.parse(msg.content)
                slots = self.__MATRIX_MC_SPELL_SLOT[pg.get_enchanter_level()]
                r = "\n".join(
                    f"{i+1} {locales[locale]['level_text']} - {slots[i]}"
                    for i in range(9)
                )
                await msg.reply(content=f"{locales[locale]['repsonse_intro']}:\n{r}")
            else:
                v = discord.ui.View(timeout=300)
                o = [discord.SelectOption(label=cls) for cls in ['barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk', 'paladin', 'ranger', 'rogue', 'sorcerer', 'warlock', 'wizard']]
                s = discord.ui.Select(min_values=1, max_values=1, options=o)
                
                async def class_parse(select_interaction: discord.Interaction):
                    pg = self.PGBuilder.single_parse(s.values[0], pg_level)
                    slots = self.__MATRIX_MC_SPELL_SLOT[pg.get_enchanter_level()]
                    r = "\n".join(
                        f"{i+1} {locales[locale]['level_text']} - {slots[i]}"
                        for i in range(9)
                    )
                    await select_interaction.response.send_message(content=f"{locales[locale]['repsonse_intro']}:\n{r}")
                
                s.callback = class_parse
                v.add_item(s)
                await interaction.followup.send(f"{locales[locale]['ask_for_class']}", view=v)
        except TimeoutError:
            await interaction.followup.send(content=locales[locale]["timeout_error"], ephemeral=False)
        except self.FormatError as e:
            logging.info(f"[5e_SpellSlotInfo] An error has occurred: Format Error - {e}")
            await interaction.followup.send(content=locales[locale]["format_error"], ephemeral=False)
        except Exception as e:
            logging.error(f"[5e_SpellSlotInfo] An error has occurred: {e}")
            logging.error(traceback.format_exc())
            await interaction.followup.send(content=locales[locale]["generic_error"], ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(SpellSlotInfo(bot))
