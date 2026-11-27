"""Trusted native player callbacks. Only the controlled player waits for HTTP input."""
import asyncio
import queue
import threading

from pyftg import AIInterface, CommandCenter, Key
from pyftg.socket.aio.gateway import Gateway


class Player(AIInterface):
    def __init__(self, session, controlled):
        self.session, self.controlled = session, controlled
        self.key = Key()
        self.audit = None

    def name(self):
        return 'GameExam' if self.controlled else 'KickAI'

    def is_blind(self):
        return not self.controlled

    def initialize(self, game_data, player_number):
        self.player = player_number
        self.cc = CommandCenter()
        if self.controlled:
            self.session.game_data = game_data.to_dict()

    def get_information(self, frame_data, is_control):
        self.data, self.is_control = frame_data, is_control
        self.cc.set_frame_data(frame_data, self.player)

    def get_non_delay_frame_data(self, frame_data):
        if self.controlled:
            self.audit = frame_data.to_dict()

    def get_screen_data(self, screen_data):
        pass

    def get_audio_data(self, audio_data):
        pass

    def processing(self):
        if self.controlled:
            if self.session.closed:
                self.key = Key()
                return
            self.session.events.put(('frame', self.data.to_dict(), self.is_control, self.audit))
            self.key = self.session.actions.get()
        elif not self.data.empty_flag and self.data.current_frame_number > 0:
            # Same key timing as the upstream pyftg KickAI example.
            if self.cc.get_skill_flag():
                self.key = self.cc.get_skill_key()
            else:
                self.key.empty()
                self.cc.skill_cancel()
                self.cc.command_call('B')

    def input(self):
        return self.key

    def round_end(self, result):
        if self.controlled:
            self.session.events.put(('round', result.to_dict()))

    def game_end(self):
        if self.controlled:
            self.session.events.put(('end',))

    def close(self):
        pass


class Session:
    def __init__(self, port, player):
        self.events, self.actions = queue.Queue(), queue.Queue()
        self.game_data = None
        self.loop = None
        self.task = None
        self.closed = False
        self.thread = threading.Thread(target=self.run, args=(port, player), daemon=True)
        self.thread.start()

    def run(self, port, player):
        async def play():
            gateway = Gateway(port=port)
            names = []
            for index in range(2):
                ai = Player(self, index == player)
                gateway.register_ai(ai.name(), ai)
                names.append(ai.name())
            await gateway.run_game(['ZEN', 'ZEN'], names, 1)
            if not self.closed:
                self.events.put(('error', 'native gateway ended before match was consumed'))
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.task = self.loop.create_task(play())
            self.loop.run_until_complete(self.task)
        except BaseException as exc:
            if not self.closed:
                self.events.put(('error', repr(exc)))
        finally:
            tasks = asyncio.all_tasks(self.loop)
            for task in tasks:
                task.cancel()
            self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            self.loop.run_until_complete(self.loop.shutdown_default_executor())
            self.loop.close()

    def next(self, timeout=10):
        try:
            event = self.events.get(timeout=timeout)
        except queue.Empty as exc:
            raise RuntimeError('native frame handshake timed out') from exc
        if event[0] == 'error':
            raise RuntimeError(event[1])
        return event

    def close(self):
        self.closed = True
        self.actions.put(Key())
        if self.loop and not self.loop.is_closed():
            if self.task:
                self.loop.call_soon_threadsafe(self.task.cancel)
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError('native Python callbacks did not stop')
