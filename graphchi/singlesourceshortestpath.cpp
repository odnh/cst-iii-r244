#include <cmath>
#include <string>
#include <limits>

#include "graphchi_basic_includes.hpp"
#include "util/labelanalysis.hpp"

using namespace graphchi;

int         iterationcount = 0;
bool        scheduler = false;

typedef vid_t VertexDataType;       // vid_t is the vertex id type
typedef vid_t EdgeDataType;

struct SSSPProgram : public GraphChiProgram<VertexDataType, EdgeDataType> {
    
    bool converged;
    
    void update(graphchi_vertex<VertexDataType, EdgeDataType> &vertex, graphchi_context &gcontext) {
        
        if (scheduler) gcontext.scheduler->remove_tasks(vertex.id(), vertex.id());
        
        if (gcontext.iteration == 0) {
            if (vertex.id() == 0) {
              vertex.set_data(0);
            } else {
              vertex.set_data(std::numeric_limits<int>::max());
            }
            if (scheduler) gcontext.scheduler->add_task(vertex.id());
        }
        
        vid_t curmin = vertex.get_data();
        for(int i=0; i < vertex.num_edges(); i++) {
            vid_t nblabel = vertex.edge(i)->get_data();
            if (gcontext.iteration == 0) nblabel = std::numeric_limits<int>::max();
            curmin = std::min(nblabel, curmin);
        }
        
        vertex.set_data(curmin);
        
        vid_t label = vertex.get_data();
        
        if (gcontext.iteration > 0) {
            for(int i=0; i < vertex.num_edges(); i++) {
                if (label+1 < vertex.edge(i)->get_data()) {
                    vertex.edge(i)->set_data(label+1);
                    if (scheduler) gcontext.scheduler->add_task(vertex.edge(i)->vertex_id(), true);
                    converged = false;
                }
            }
        } else if (gcontext.iteration == 0) {
            for(int i=0; i < vertex.num_outedges(); i++) {
                vertex.outedge(i)->set_data(label);
            }
        }
    } 

    void before_iteration(int iteration, graphchi_context &info) {
        iterationcount++;
        converged = iteration > 0;
    }
    
    void after_iteration(int iteration, graphchi_context &ginfo) {
        if (converged) {
            std::cout << "Converged!" << std::endl;
            ginfo.set_last_iteration(iteration);
        }
    }
    
    void before_exec_interval(vid_t window_st, vid_t window_en, graphchi_context &ginfo) {        
    }
    
    void after_exec_interval(vid_t window_st, vid_t window_en, graphchi_context &ginfo) {        
    }
    
};

int main(int argc, const char ** argv) {
    graphchi_init(argc, argv);

    metrics m("sssp");
    
    std::string filename = get_option_string("file");  // Base filename
    int niters           = get_option_int("niters", 1000); // Number of iterations (max)
    scheduler            = get_option_int("scheduler", false);
    
    /* Process input file - if not already preprocessed */
    int nshards             = (int) convert_if_notexists<EdgeDataType>(filename, get_option_string("nshards", "auto"));
    
    if (get_option_int("onlyresult", 0) == 0) {
        SSSPProgram program;
        graphchi_engine<VertexDataType, EdgeDataType> engine(filename, nshards, scheduler, m); 
        engine.run(program, niters);
    }
    
    m.start_time("label-analysis");
    
    analyze_labels<vid_t>(filename);
    
    m.stop_time("label-analysis");
    
    /* Report execution metrics */
    metrics_report(m);
    return 0;
}
