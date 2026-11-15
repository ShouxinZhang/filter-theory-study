#include "baseline/cli.hpp"
#include "baseline/grid_reference.hpp"
#include "baseline/io.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
// 索引只含观测路径，求后验时无真值输入，评价在独立程序完成。
int main(int argc, char** argv) {
    try {
        using namespace baseline; Args args(argc, argv);
        std::ifstream index(args.require("index")); std::string line;
        if (!std::getline(index, line) || line != "observations_path") throw std::runtime_error("索引表头错误");
        std::vector<std::vector<Observation>> data;
        while (std::getline(index, line)) data.push_back(read_observations(line));
        auto result = grid_reference(Model(args.get("model", "gordon")), data,
            args.real("bound", 60), args.real("spacing", 0.1), args.integer("interval", 1));
        for (size_t b = 0; b < data.size(); ++b) {
            std::ostringstream name; name << "trial_" << std::setw(4) << std::setfill('0') << b;
            write_records(std::filesystem::path(args.require("output")) / name.str() / "filter.csv", result.records[b]);
        }
        std::ostringstream diagnostic;
        diagnostic << std::setprecision(17) << "max_prediction_mass_error\n" << result.max_prediction_mass_error << '\n';
        atomic_text(std::filesystem::path(args.require("output")) / "diagnostics.csv", diagnostic.str());
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
