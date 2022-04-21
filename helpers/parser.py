from aiotfm import Packet


class Profile:
    """Represents a player's profile.

    Attributes
    ----------
    username: `str`
        The player's username.
    uid: `int`
        The player's id.
    registration_date: `int`
        The registration timestamp of the player.
    privLevel: `int`
        The privilege level of the player.
    gender: `int`
        Player's gender.
    tribe: `str`
        Player's tribe. Can be `None`.
    soulmate: `str`
        Player's soulmate. Can be `None`.
    title: `int`
        The title above the player's head.
    titles: `set`
        The list of the unlocked titles.
    titles_stars: `dict`
        A dictionary where are stored the number of stars a title has.
    look: `str`
        The player's look.
    level: `int`
        The player's shaman level.
    badges: `dict`
        All badges unlocked by the player and their number.
    stats: `Stats`
        The player's stats.
    equippedOrb: `int`
        The equipped orb of the player.
    orbs: `set`
        The list of unlocked orbs.
    adventurePoints: `int`
        Number of adventure points the player has.
    """
    def __init__(self, packet: Packet):
        self.username = packet.readUTF()
        self.id = packet.read32()

        self.registration_date = packet.read32()
        self.privLevel = packet.read8()
        self.gender = packet.read8()
        self.tribe = packet.readUTF() or None
        self.soulmate = packet.readUTF() or None
        stats = [packet.read32() for i in range(10)]
        self.title = packet.read16()

        self.titles = set()
        self.titles_stars = {}
        for _ in range(packet.read16()):
            title_id, stars = packet.read16(), packet.read8()
            self.titles.add(title_id)
            if stars > 1:
                self.titles_stars[title_id] = stars

        self.look = packet.readUTF()
        self.level = packet.read16()

        self.badges = {}
        for _ in range(round(packet.read16() / 2)):
            badge, quantity = packet.read16(), packet.read16()
            self.badges[badge] = quantity

        modeStats = []
        for _ in range(packet.read8()):
            modeStats.append((packet.read8(), packet.read32(), packet.read32(), packet.read16()))
        self.stats = Stats(stats, modeStats)

        self.equippedOrb = packet.read8()
        self.orbs = set()
        for _ in range(packet.read8()):
            self.orbs.add(packet.read8())

        packet.readBool()
        self.adventurePoints = packet.read32()


class Stats:
    """Represents the statistics of a player.

    Attributes
    ----------
    normalModeSaves: `int`
        Number of shaman saves in normal mode.
    hardModeSaves: `int`
        Number of shaman saves in hard mode.
    divineModeSaves: `int`
        Number of shaman saves in divine mode.
    shamanCheese: `int`
        Number of cheese personally gathered.
    firsts: `int`
        Number of cheese gathered first.
    gatheredCheese: `int`
        Total number of gathered cheese.
    bootcamps: `int`
        Number of bootcamp.
    modeStats: `list`
        A list of tuples that represents the stats in different mode.
        (id, progress, progressLimit, imageId)
    """
    def __init__(self, stats, modeStats):
        self.normalModeSaves = stats[0]
        self.hardModeSaves = stats[4]
        self.divineModeSaves = stats[6]
        self.shamanCheese = stats[1]
        self.firsts = stats[2]
        self.gatheredCheese = stats[3]
        self.bootcamps = stats[5]
        self.withoutSkillSaves = stats[7]

        self.modeStats = modeStats # id, progress, progressLimit, imageId
