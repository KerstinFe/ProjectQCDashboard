"""Tests for Observer module."""

from unittest.mock import Mock, patch
from pathlib import Path
from queue import Queue
import threading
from ProjectQCDashboard.background.observer import myHandler, Observer_DBs, start_observer


class TestMyHandler:
    """Test suite for myHandler class."""

    @patch("ProjectQCDashboard.background.observer.external_mqqc", ["/test/database.db"])
    @patch("ProjectQCDashboard.background.observer.external_meta", "/test/meta.db")
    def test_init(self) -> None:
        q: Queue[str | Path] = Queue()
        watchedfiles = ["/test/database.db", "/test/meta.db"]
        handler = myHandler(q, watched_files= watchedfiles)
        assert handler.q is q
        assert isinstance(handler.DB, list)
        assert "/test/database.db" in handler.DB
        assert "/test/meta.db" in handler.DB


    @patch("ProjectQCDashboard.background.observer.external_mqqc", ["/test/database.db"])
    @patch("ProjectQCDashboard.background.observer.external_meta", "/test/meta.db")
    def test_on_modified_matching_db(self) -> None:
        q: Queue[str | Path] = Queue()
        watchedfiles = ["/test/database.db", "/test/meta.db"]
        handler = myHandler(q, watched_files= watchedfiles)
        mock_event = Mock()
        mock_event.src_path = "/test/database.db"
        handler.on_modified(mock_event)
        assert not q.empty()
        assert q.get() == "/test/database.db"


    @patch("ProjectQCDashboard.background.observer.external_mqqc", ["/test/database.db"])
    @patch("ProjectQCDashboard.background.observer.external_meta", "/test/meta.db")
    def test_on_modified_non_matching_db(self) -> None:
        q: Queue[str | Path] = Queue()
        watchedfiles = ["/test/database.db", "/test/meta.db"]
        handler = myHandler(q, watched_files= watchedfiles)
        mock_event = Mock()
        mock_event.src_path = "/test/other.db"
        handler.on_modified(mock_event)
        assert q.empty()


    @patch("ProjectQCDashboard.background.observer.external_mqqc", ["/test/database.db"])
    @patch("ProjectQCDashboard.background.observer.external_meta", "/test/meta.db")
    def test_on_created_matching_db(self) -> None:
        q: Queue[str | Path] = Queue()
        watchedfiles = ["/test/database.db", "/test/meta.db"]
        handler = myHandler(q, watched_files= watchedfiles)
        mock_event = Mock()
        mock_event.src_path = "/test/database.db"
        handler.on_created(mock_event)
        assert not q.empty()
        assert q.get() == "/test/database.db"



class TestObserverDBs:
    """Test suite for Observer_DBs class."""

    @patch("ProjectQCDashboard.background.observer.DB_Paths_towatch", ["/dir1", "/dir2"])
    def test_init(self) -> None:
        q: Queue[str | Path] = Queue()
        observer = Observer_DBs(q)
        assert set(observer.DB_Paths_towatch) == {"/dir1", "/dir2"}
        assert observer.Observer_list == []
        assert observer.q is q


    @patch("ProjectQCDashboard.background.observer.DB_Paths_towatch", ["/dir1", "/dir2"])
    @patch("ProjectQCDashboard.background.observer.start_observer")
    def test_start_observing_success(self, mock_start_observer: Mock) -> None:
        mock_observer1 = Mock()
        mock_observer2 = Mock()
        mock_start_observer.side_effect = [mock_observer1, mock_observer2]
        q: Queue[str | Path] = Queue()
        observer = Observer_DBs(q)
        stop_event = threading.Event()
        # Set stop_event after one loop
        def set_stop() -> None:
            stop_event.set()
        threading.Timer(0.1, set_stop).start()
        observer.start_observing(stop_event)
        assert len(observer.Observer_list) == 2
        assert mock_start_observer.call_count == 2

    @patch("ProjectQCDashboard.background.observer.DB_Paths_towatch", ["/dir1", "/dir2"])
    @patch("ProjectQCDashboard.background.observer.start_observer")
    def test_start_observing_with_failure(self, mock_start_observer: Mock) -> None:
        mock_observer = Mock()
        mock_start_observer.side_effect = [mock_observer, Exception("Failed to start")]
        q: Queue[str | Path] = Queue()
        observer = Observer_DBs(q)
        stop_event = threading.Event()
        def set_stop() -> None:
            stop_event.set()
        threading.Timer(0.1, set_stop).start()
        observer.start_observing(stop_event)
        assert len(observer.Observer_list) == 1  # Only one observer started

    def test_closing_observations(self) -> None:
        q: Queue[str | Path] = Queue()
        observer = Observer_DBs(q)
        mock_observer1 = Mock()
        mock_observer1.is_alive.return_value = True
        mock_observer2 = Mock()
        mock_observer2.is_alive.return_value = True
        observer.Observer_list = [mock_observer1, mock_observer2]
        observer.close_observations()
        mock_observer1.stop.assert_called_once()
        mock_observer1.join.assert_called_once()
        mock_observer2.stop.assert_called_once()
        mock_observer2.join.assert_called_once()

    def test_closing_observations_with_dead_observer(self) -> None:
        q: Queue[str | Path] = Queue()
        observer = Observer_DBs(q)
        mock_observer1 = Mock()
        mock_observer1.is_alive.return_value = False
        mock_observer2 = Mock()
        mock_observer2.is_alive.return_value = True
        observer.Observer_list = [mock_observer1, mock_observer2]
        observer.close_observations()
        mock_observer1.stop.assert_not_called()
        mock_observer2.stop.assert_called_once()


class TestStartObserver:
    """Test suite for start_observer function."""

    @patch("ProjectQCDashboard.background.observer.PollingObserver")
    def test_start_observer_success(self, mock_observer_class: Mock) -> None:
        handler = Mock()
        watch_dir = "/test/dir"
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        result = start_observer(handler, watch_dir)
        assert result == mock_observer
        mock_observer.schedule.assert_called_once_with(handler, path=watch_dir, recursive=False)
        mock_observer.start.assert_called_once()
