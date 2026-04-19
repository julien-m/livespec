import { redirect } from 'some-router';

export const Route = { path: '/profile' };

export default function ProfilePage() {
  redirect('/login');
  return null;
}
