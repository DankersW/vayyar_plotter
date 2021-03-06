from yaml import safe_load
from time import time
from datetime import datetime
from typing import Tuple
from decimal import Decimal
from operator import itemgetter

from dataclasses import dataclass

from matplotlib import pyplot, animation

from db_driver import DbDriver


class LivePlotter:
    def __init__(self, config: dataclass):
        if config.live_monitor:
            self.db_room = DbDriver(keys=self._get_keys(), table='vayyar_home_c2c_room_status')
            self.db_fall = DbDriver(keys=self._get_keys(), table='vayyar_home_c2c_fall_data')

            self.start_timestamp = round(time() * 1000)

            fig = pyplot.figure()
            self.live_plot = fig.add_subplot(2, 2, 1)
            self.live_table = fig.add_subplot(2, 2, 2)
            self.yesterday_plot = fig.add_subplot(2, 2, 3)

            _ = animation.FuncAnimation(fig, self.plot_live, interval=5000)
            self.plot_past_room_occupation()

            pyplot.setp(self.live_plot.get_xticklabels(), rotation=30, ha='right')
            pyplot.setp(self.yesterday_plot.get_xticklabels(), rotation=30, ha='right')
            pyplot.show()

    @staticmethod
    def _get_keys():
        with open("keys.yml") as config_file:
            return safe_load(config_file)

    def plot_live(self, _):
        presence_data = self.db_room.query_db(oldest_timestamp=self.start_timestamp)
        fall_data = self.db_fall.query_db(oldest_timestamp=self.start_timestamp)
        self._plot_data(sub_plot=self.live_plot, data=presence_data)
        self.show_events(presence_data=presence_data, fall_data=fall_data)
        self.live_plot.set_title("Live monitoring")

    def show_events(self, presence_data, fall_data):
        if not presence_data and not fall_data:
            return
        data = self._combine_data_tables(presence_data=presence_data, fall_data=fall_data)
        table_data = []
        for item in data:
            dt = self._decimal_timestamp_to_dt(timestamp=item.get('timestamp'))
            msg = self._fetch_event_msg(entry=item)
            li = [dt, msg]
            table_data.append(li)
        self.live_table.axis('tight')
        self.live_table.axis('off')
        self.live_table.table(cellText=table_data, colLabels=["timestamp", "event"])

    @staticmethod
    def _combine_data_tables(presence_data: list, fall_data: list) -> list:
        data = []
        prev_room_status = None
        for item in presence_data:
            if item.get('room_occupied') != prev_room_status:
                prev_room_status = item.get('room_occupied')
                data.append(item)
        data += fall_data
        return sorted(data, key=itemgetter('timestamp'))

    @staticmethod
    def _fetch_event_msg(entry: dict) -> str:
        if 'fall_status' in entry:
            return entry.get('fall_status')
        elif 'room_occupied' in entry:
            return f"room occupied: {entry.get('room_occupied')}"
        else:
            print(entry)

    @staticmethod
    def days_to_millisec(days: int) -> int:
        return days * 86400000

    def plot_past_room_occupation(self):
        past_days = 3
        timestamp_yesterday = self.start_timestamp - self.days_to_millisec(days=past_days)
        data = self.db_room.query_db(oldest_timestamp=timestamp_yesterday, untill_timestamp=self.start_timestamp)
        self._plot_data(sub_plot=self.yesterday_plot, data=data)
        self.yesterday_plot.set_title(f"Occupance past {past_days} day(s)")

    def _plot_data(self, sub_plot: pyplot.subplot, data: list):
        x = []
        y = []
        for item in data:
            dt, room_occupied = self._parse_data_entry(entry=item)
            x.append(dt)
            y.append(room_occupied)
        sub_plot.step(x, y)

    def _parse_data_entry(self, entry: dict) -> Tuple[datetime, int]:
        dt = self._decimal_timestamp_to_dt(timestamp=entry.get("timestamp"))
        occupied = 1 if entry.get("room_occupied") else 0
        return dt, occupied

    @staticmethod
    def _decimal_timestamp_to_dt(timestamp: Decimal) -> datetime:
        return datetime.fromtimestamp(timestamp.__int__() / 1000)


if __name__ == '__main__':
    LivePlotter()
