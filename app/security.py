"""Password hashing.

A replacement for ``werkzeug.security`` that keeps the same hash format, so
the passwords that are already stored in the database remain valid.
"""
import hashlib
import hmac
import secrets

SALT_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
# scrypt needs OpenSSL 1.1 or newer, pbkdf2 is used when it is not available
DEFAULT_METHOD = 'scrypt' if hasattr(hashlib, 'scrypt') else 'pbkdf2:sha256'
DEFAULT_PBKDF2_ITERATIONS = 600000


def gen_salt(length=16):
    """Generate a random string of the given length."""
    if length <= 0:
        raise ValueError('Salt length must be at least 1.')
    return ''.join(secrets.choice(SALT_CHARS) for _ in range(length))


def _hash_internal(method, salt, password):
    method, *args = method.split(':')
    salt_bytes = salt.encode()
    password_bytes = password.encode()

    if method == 'scrypt':
        if not hasattr(hashlib, 'scrypt'):
            raise NotImplementedError(
                'This installation of Python does not support scrypt.')
        if not args:
            n = 2 ** 15
            r = 8
            p = 1
        else:
            try:
                n, r, p = map(int, args)
            except ValueError:
                raise ValueError(
                    'scrypt requires "n", "r", and "p".') from None
        maxmem = 132 * n * r * p  # ideally 128, but some extra seems needed
        return (
            hashlib.scrypt(password_bytes, salt=salt_bytes, n=n, r=r, p=p,
                           maxmem=maxmem, dklen=64).hex(),
            f'scrypt:{n}:{r}:{p}',
        )
    elif method == 'pbkdf2':
        if len(args) == 0:
            hash_name = 'sha256'
            iterations = DEFAULT_PBKDF2_ITERATIONS
        elif len(args) == 1:
            hash_name = args[0]
            iterations = DEFAULT_PBKDF2_ITERATIONS
        elif len(args) == 2:
            hash_name = args[0]
            iterations = int(args[1])
        else:
            raise ValueError('pbkdf2 takes 2 arguments.')
        return (
            hashlib.pbkdf2_hmac(hash_name, password_bytes, salt_bytes,
                                iterations).hex(),
            f'pbkdf2:{hash_name}:{iterations}',
        )
    else:
        raise ValueError(f'Invalid hash method {method!r}.')


def generate_password_hash(password, method=DEFAULT_METHOD, salt_length=16):
    """Hash a password, returning it as ``method$salt$hash``."""
    salt = gen_salt(salt_length)
    hashed, actual_method = _hash_internal(method, salt, password)
    return f'{actual_method}${salt}${hashed}'


def check_password_hash(pwhash, password):
    """Check a password against a hash made by generate_password_hash()."""
    try:
        method, salt, hashval = pwhash.split('$', 2)
    except ValueError:
        return False
    if not method or not salt:
        return False
    try:
        return hmac.compare_digest(_hash_internal(method, salt, password)[0],
                                   hashval)
    except ValueError:
        return False
