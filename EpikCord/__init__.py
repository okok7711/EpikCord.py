"""
:license:
Some parts of the code is sourced from discord.py
The MIT License (MIT)
Copyright © 2015-2021 Rapptz
Copyright © 2021-present EpikHost
Permission is hereby granted, free of charge, to any person obtaining a copy of 
this software and associated documentation files (the “Software”), to deal in 
the Software without restriction, including without limitation the rights to 
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
of the Software, and to permit persons to whom the Software is furnished to do 
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, RESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""

from .abstract import *
from .application import *
from .auto_moderation import *
from .channels import *
from .client import *
from .close_event_codes import *
from .colour import *
from .commands import *
from .components import *
from .exceptions import *
from .flags import *
from .guild import *
from .interactions import *
from .localizations import *
from .managers import *
from .mentioned import *
from .message import *
from .opcodes import *
from .options import *
from .partials import *
from .presence import *
from .rtp_handler import *
from .sharding import *
from .status_code import *
from .sticker import *
from .thread import *
from .type_enums import *
from .user import *
from .utils import *
from .voice import *
from .webhooks import *

__version__ = "0.5.4"
__all__ = ("__version__",)
