import logging
import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands
from math import floor

locales = {
    "it":   {
        "ask_for_classes": "Mi potresti dare le classi del tuo pg? Per favore, segui la seguente leggenda",
        "legend": "class:level\nE.g.:\n'warlock:1, cleric:2, wizard:6'",
        "level_text": "livello",
        "repsonse_intro": "Hai i seguenti slot incantesimo",
        "generic_error": "Si è verificato un errore",
        "timeout_error": "Ti ho dato due minuti, eh. Devi fare più in fretta :)",
        "format_error": "No, zì, non sto a capì niente. Per favore, riprova il comando e segui la formattazione :)",
    },
    "eng":  {
        "ask_for_classes": "Can you give me the classes of your pg? Please, refer to the following legend",
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
                self.barbarian = None
                self.bard = None
                self.cleric = None
                self.druid = None
                self.fighter = None
                self.monk = None
                self.paladin = None
                self.ranger = None
                self.rogue = None
                self.sorcerer = None
                self.warlock = None
                self.wizard = None

            def add_level(self, cls: str, level: int) -> None:
                if cls == "barbarian":
                    self.barbarian = level
                if cls == "bard":
                    self.bard = level
                if cls == "cleric":
                    self.cleric = level
                if cls == "druid":
                    self.druid = level
                if cls == "fighter":
                    self.fighter = level
                if cls == "monk":
                    self.monk = level
                if cls == "paladin":
                    self.paladin = level
                if cls == "ranger":
                    self.ranger = level
                if cls == "rogue":
                    self.rogue = level
                if cls == "sorcerer":
                    self.sorcerer = level
                if cls == "warlock":
                    self.warlock = level
                if cls == "wizard":
                    self.wizard = level

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
        def parse(self, m: str) -> PG:
            self.p = self.PG()
            m = m.strip().lower().replace(" ", "").split(",")
            for c in m:
                cl, l = c.split(":")[0], c.split(':')[1]
                self.p.add_level(cl, l)
            return self.p

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="spell_slots_info",
        description="Get how many spell slots your pg has"
    )
    @app_commands.describe(pg_level="Level of your PG", multiclass="If your pg has multiclassed")
    @app_commands.Group(name="5e info")
    async def spell_slot_info(self, interaction: discord.Interaction, pg_level: int, multiclass: Optional[bool] = False):
        locale = interaction.locale if interaction.locale in locales else "eng"
        if multiclass:
            interaction.response.defer()
            try:
                # 2 min to let the user write the classes
                interaction.response.send_message(f"{locales[locale]['ask_for_classes']} - {locales[locale]['legend']}")
                msg = await interaction.client.wait_for('message', timeout=120)
                pg = self.PGBuilder.parse(msg)

                slots = self.__MATRIX_MC_SPELL_SLOT[pg.get_enchanter_level()]
                r = f"""
1 {locales[locale]['level_text']} - {slots[0]}
2 {locales[locale]['level_text']} - {slots[1]}
3 {locales[locale]['level_text']} - {slots[2]}
4 {locales[locale]['level_text']} - {slots[3]}
5 {locales[locale]['level_text']} - {slots[4]}
6 {locales[locale]['level_text']} - {slots[5]}
7 {locales[locale]['level_text']} - {slots[6]}
8 {locales[locale]['level_text']} - {slots[7]}
9 {locales[locale]['level_text']} - {slots[8]}
"""
                await msg.reply(content=f"{locales[locale]['response_intro']}:\n{r}")
            except TimeoutError as e:
                await interaction.followup.send(content=locales[locale]["timeout_error"], ephemeral=False)
            except self.FormatError as e:
                logging.info(f"[5e_SpellSlotInfo] An error has occurred: Format Error - {e}")
                await interaction.followup.send(content=locales[locale]["format_error"], ephemeral=False)
            except Exception as e:
                logging.error(f"[5e_SpellSlotInfo] An error has occurred: {e}")
                await interaction.followup.send(content=locales[locale]["generic_error"], ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(SpellSlotInfo(bot))
