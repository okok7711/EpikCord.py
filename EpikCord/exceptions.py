class DiscordAPIError(Exception): # 
    ...
    
class InvalidToken(Exception):
    ...

class BadRequest400(Exception):
    ...

class Unauthorized401(Exception):
    ...

class Forbidden403(Exception):
    ...

class NotFound404(Exception):
    ...

class MethodNotAllowed405(Exception):
    ...
    
class Ratelimited429(Exception):
    ...

class GateawayUnavailable502(Exception):
    ...
    
class InternalServerError5xx(Exception):
    ...
    
class TooManyComponents(Exception):
    ...

class InvalidMessageButtonStyle(Exception):
    ...

