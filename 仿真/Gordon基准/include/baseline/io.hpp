#pragma once
#include "baseline/types.hpp"
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
namespace baseline {
std::vector<std::string> split(const std::string& line);
std::vector<Observation> read_observations(const std::filesystem::path& path);
std::vector<Truth> read_truth(const std::filesystem::path& path);
std::vector<Record> read_records(const std::filesystem::path& path);
void write_records(const std::filesystem::path& path,const std::vector<Record>& rows);
void prepare_parent(const std::filesystem::path& path);
void atomic_text(const std::filesystem::path& path,const std::string& text);
}
