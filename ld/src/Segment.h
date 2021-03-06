#ifndef LDSERVER_SEGMENT_H
#define LDSERVER_SEGMENT_H

#include <stdexcept>
#include <iostream>
#include <vector>
#include <string>
#include <savvy/armadillo_vector.hpp>
#include <hiredis/hiredis.h>
#include <cereal/archives/binary.hpp>
#include <cereal/types/string.hpp>
#include <cereal/types/vector.hpp>
#include <savvy/reader.hpp>
#include <savvy/armadillo_vector.hpp>
#include "Types.h"

using namespace std;

class Segment {
private:
    bool cached;
    bool names_loaded;
    bool genotypes_loaded;

    string chromosome;
    uint64_t start_bp;
    uint64_t stop_bp;
    uint64_t n_haplotypes;
    vector<string> names;
    vector<uint64_t> positions;

    vector<arma::uword> sp_mat_rowind;
    vector<arma::uword> sp_mat_colind;
public:
    Segment(const string& chromosome, uint64_t start_bp, uint64_t stop_bp);
    Segment(Segment&& segment);
    virtual ~Segment();

    void clear();
    void clear_names();
    void clear_genotypes();
    void add(savvy::site_info& anno, savvy::armadillo::sparse_vector<float>& alleles);
    void add_name(savvy::site_info& anno, savvy::armadillo::sparse_vector<float>& alleles);
    void add_genotypes(savvy::armadillo::sparse_vector<float>& alleles);
    void freeze();
    void freeze_names();
    void freeze_genotypes();

    void load(redisContext* redis_cache, const string& key);
    void save(redisContext* redis_cache, const string& key);

    bool is_empty() const;
    bool is_cached() const;
    bool has_names() const;
    bool has_genotypes() const;

    const char* get_key() const;
    uint64_t get_key_size() const;
    const string& get_chromosome() const;
    uint64_t get_start_bp() const;
    uint64_t get_stop_bp() const;
    uint64_t get_n_haplotypes() const;
    uint32_t get_n_variants() const;
    const string& get_name(int i) const;
    uint64_t get_position(int i) const;
    arma::sp_fmat get_genotypes();

    static void create_pair(Segment& segment1, Segment& segment2, int index_i, int index_j, double value, vector<VariantsPair>& pairs);

    bool overlaps_region(uint64_t region_start_bp, uint64_t region_stop_bp, int& from_index, int& to_index) const;
    bool overlaps_variant(const string& name, uint64_t bp, int& index) const;

    template <class Archive>
    void load( Archive & ar )
    {
        ar( n_haplotypes, names, positions );
    }

    template <class Archive>
    void save( Archive & ar ) const
    {
        ar( n_haplotypes, names, positions );
    }
};

#endif
