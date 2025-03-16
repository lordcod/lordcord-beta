from . import guildHD, economyHD, commandHD, rolesHD, mongoHD, bansHD

from .guildHD import GuildDateBases
from .economyHD import EconomyMemberDB
from .commandHD import CommandDB
from .rolesHD import RoleDateBases
from .bansHD import BanDateBases
from .mongoHD import MongoDB


def establish_connection(conn):
    guildHD.engine = conn
    economyHD.engine = conn
    commandHD.engine = conn
    rolesHD.engine = conn
    bansHD.engine = conn
    mongoHD.engine = conn
