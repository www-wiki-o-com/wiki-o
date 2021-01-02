r""" __      __    __               ___
    /  \    /  \__|  | _ __        /   \
    \   \/\/   /  |  |/ /  |  __  |  |  |
     \        /|  |    <|  | |__| |  |  |
      \__/\__/ |__|__|__\__|       \___/

Copyright (C) 2018 Wiki-O, Frank Imeson

This source code is licensed under the GPL license found in the
LICENSE.md file in the root directory of this source tree.
"""

# *******************************************************************************
# Imports
# *******************************************************************************
import random
import base64

# *******************************************************************************
# Defines
# *******************************************************************************
DEBUG = False

# *******************************************************************************
# Converters
# *******************************************************************************


class IntegerCypher:
    """IntegerCypher is a reversible keyed permutation for integers.

    This class is not cryptographically secure as the F function is too simple and there are
    not enough rounds.

    Original Author: Martin Ross
    Original Source: https://stackoverflow.com/a/7285459/1891461

    Attributes:
    """

    regex = r'([A-Za-z0-9\-_=]+)'

    @classmethod
    def generate_keys(cls, seed, key_length=16, num_rounds=4):
        """Sets a new value for the key and key schedule.

        Args:
            key (int): The new private key.
        """
        keys = []
        random.seed(seed)
        mask = 2**key_length - 1
        for _ in range(num_rounds):
            keys.append(random.randint(mask // 2, mask) & mask)
        return keys

    def __init__(self, bit_length=32, keys=None):
        """[summary]

        Returns:
            [type]: [description]

        Raises:
            ValueError: If bit_length is not a multiple of 8.
        """
        # Preconditions
        if bit_length % 8 != 0:
            raise ValueError(f'bit_length ({bit_length}) needs to be a multiple of 8.')
        # Populate helper attributes and keys.
        self.half_length = bit_length // 2
        self.num_bytes = bit_length // 8
        self.low_mask = 2**self.half_length - 1
        if keys is None:
            keys = self.generate_keys(seed=0x6CFB18E2, key_length=self.half_length)
        self.keys = keys

    def __call__(self):
        return self

    def encrypt(self, plain):
        """Calculates the encrypted, i.e., the permuted value of the given integer.

        Returns:
            int: The encrypted (permuted) value.
        """
        # Step 1: Split into two halves.
        rhs = plain & self.low_mask
        lhs = plain >> self.half_length

        # Step 2: Do 4 simple Feistel rounds.
        for i, round_key in enumerate(self.keys):
            if i > 0:
                # Swap lhs <-> rhs
                lhs, rhs = rhs, lhs
            # Apply Feistel round function F().
            rhs = rhs ^ self.feistel_round(lhs, round_key)

        # Step 3: Recombine the two halves and return.
        x = (lhs << self.half_length) + (rhs & self.low_mask)

        # Step 4: Integer to Ascii.
        return base64.urlsafe_b64encode(x.to_bytes(self.num_bytes, byteorder='big'))

    def decrypt(self, cypher):
        """Calculates the decrypted value of the given integer.

        Args:
            cypher (int): The integer to decrypt.

        Returns:
            int: The decrypted (inverse permuted) value.
        """
        # Step 0: Ascii to integer.
        cypher = int.from_bytes(base64.urlsafe_b64decode(cypher), byteorder='big')

        # Step 1: Split into two halves.
        rhs = cypher & self.low_mask
        lhs = cypher >> self.half_length

        # Step 2: Do 4 simple Feistel rounds.
        n = len(self.keys)
        for i in range(len(self.keys)):
            if i > 0:
                # Swap lhs <-> rhs
                lhs, rhs = rhs, lhs
            # Apply Feistel round function F().
            rhs = rhs ^ self.feistel_round(lhs, self.keys[n - 1 - i])

        # Step 3: Recombine the two halves and return.
        return (lhs << self.half_length) + (rhs & self.low_mask)

    def feistel_round(self, num, round_key):
        """The F function for the Feistel rounds.

        Returns:
            int: The permuted value
        """
        # XOR with round key.
        num = num ^ round_key
        # Square (this step doesn't appear to be standard Feistel).
        num = num * num
        # XOR the high and low parts.
        return (num >> self.half_length) ^ (num & self.low_mask)

    def to_python(self, value):
        return self.decrypt(value)

    def to_url(self, value):
        return str(self.encrypt(value))[2:-1]
