import { HeroSection } from "@/components/home/HeroSection";
import { StatsBar } from "@/components/home/StatsBar";
import { FeaturesSection } from "@/components/home/FeaturesSection";

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <StatsBar />
      <FeaturesSection />
    </>
  );
}
