from datetime import datetime, time
from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36


class PasswordTokenGenerator:
    key_salt = "django.contrib.auth.tokens.PasswordResetTokenGenerator"
    secret = settings.SECRET_KEY

    def make_token(self, user):
        return self._make_token_with_timestamp(user, self._num_seconds(self._now()))

    def check_token(self, user, token):
        if not (user and token):
            return False
        # Parse the token
        try:
            ts_b36, _ = token.split("-")
            legacy_token = len(ts_b36) < 4
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(user, ts), token):
            if not constant_time_compare(
                self._make_token_with_timestamp(user, ts, legacy=True),
                token,
            ):
                return False

        now = self._now()
        if legacy_token:
            ts *= 24 * 60 * 60
            ts += int((now - datetime.combine(now.date(), time.min)).total_seconds())
        # Check the timestamp is within limit.
        if (self._num_seconds(now) - ts) > settings.PASSWORD_RESET_TOKEN_TIMEOUT:
            return False
        return True

    def _make_token_with_timestamp(self, user, timestamp, legacy=False):
        # timestamp is number of seconds since 2001-1-1. Converted to base 36,
        # this gives us a 6 digit string until about 2069.
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(user, timestamp),
            secret=self.secret,
        ).hexdigest()[::2]  # Limit to 20 characters to shorten the URL.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, user, timestamp):
        # Truncate microseconds so that tokens are consistent even if the
        # database doesn't support microseconds.
        login_timestamp = '' if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        return str(user.pk) + user.password + str(login_timestamp) + str(timestamp)

    def _num_seconds(self, dt):
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _now(self):
        # Used for mocking in tests
        return datetime.now()


password_reset_token = PasswordTokenGenerator()
