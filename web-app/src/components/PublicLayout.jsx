import { Outlet } from 'react-router-dom';
import PublicFooter from './PublicFooter';
import PublicHeader from './PublicHeader';

export default function PublicLayout() {
  return (
    <>
      <PublicHeader />
      <main style={{ paddingTop: 80 }}>
        <Outlet />
      </main>
      <PublicFooter />
    </>
  );
}
