"""instantiate global ShowBase object"""

from game.otp.ai.AIBase import *

# We're going to end up importing this accidentally anyway, so we
# might as well import it explicitly, and share the same AIBase
# object.
from game.otp.ai.AIBaseGlobal import *

__builtins__["uber"] = simbase
