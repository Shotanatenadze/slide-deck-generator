import { GenerationProvider } from './providers';
import { MainLayout } from '@/components/layout/main-layout';

export default function Home() {
  return (
    <GenerationProvider>
      <MainLayout />
    </GenerationProvider>
  );
}
