import bcrypt from 'bcrypt';

export async function hashPassword(plain) {
  const rounds = parseInt(process.env.BCRYPT_ROUNDS || '10');
  return bcrypt.hash(plain, rounds);
}

export async function comparePassword(plain, hash) {
  return bcrypt.compare(plain, hash);
}
