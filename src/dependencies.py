_controller = None


def set_controller(controller):
    global _controller
    _controller = controller


def get_controller():
    return _controller
