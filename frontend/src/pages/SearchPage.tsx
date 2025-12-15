import Search from "../Search";
import SectionHeader from "../ui/SectionHeader";

export default function SearchPage() {
  return (
    <div>
      <SectionHeader
        title="Search"
        description="Find tickets, inspect details, and leave feedback."
      />
      <Search />
    </div>
  );
}
