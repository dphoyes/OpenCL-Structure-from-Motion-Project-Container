SHELL := /bin/zsh

# soc_host := 95.145.62.162
soc_host := socfpga
sfm_params := -f672 -u672 -v186 -h1.2 -p0 -n40

time_patterns := 'FPS' 'Estimate F time' 'Best plane time' 'fpga_area'

sfm_sources := $(shell find src -type f)
sfm_impls := $(shell cd src && git tag) current
sfm_impls_arm := $(shell cd src && git tag | grep -E '^[^x]') current
sfm_impls_x86 := $(shell cd src && git tag | grep -E '^[^a]') current

graph_specs := $(shell find Reports/graph_specs -type f)

default: testx86

testx86:  results/x86/fps.png
testarm:  results/arm/fps.png
testall:  results/fps.png

list_impls:
	@echo $(sfm_impls)

Reports/images/graphs/%.png: Reports/graph_specs/% scripts/plot_fps.py
	@mkdir -p $(dir $@)
	scripts/plot_fps.py src results $< $(dir $@)

Reports/calltree/%.png: Reports/calltree/%
	cd $(dir $@) && dot $(notdir $<) -Tpng -O

images: $(foreach i,$(graph_specs),Reports/images/graphs/$(notdir $(i)).png) $(foreach i,calls estimatef plane,Reports/calltree/$(i).dot.png)

#build
build/x86/Makefile: src/CMakeLists.txt
	@mkdir -p $(@D)
	@cd $(@D) && cmake ../../src

build/arm/Makefile: src/CMakeLists.txt
	@mkdir -p $(@D)
	@cd $(@D) && cmake ../../src -DCMAKE_TOOLCHAIN_FILE=../../src/arm-linux-gnueabihf.toolchain.cmake

build/%/sfm: build/%/Makefile $(sfm_sources)
	@cd $(@D) && $(MAKE) --no-print-directory
	@touch $@

#checkout
checkout_goto-%:
	@[ -z "`cd src && git status --porcelain`" ] || (echo Need to checkout previous version. Please commit all changes. && false)
	cd src && git checkout $*
	touch src/CMakeLists.txt

checkout_return:
	cd src && git checkout master
	touch src/CMakeLists.txt

#x86
gen_results_dir_x86-%: build/x86/sfm
	@mkdir -p results/x86/$*
	build/x86/sfm $(sfm_params) -o results/x86/$*/viso_cloud.ply video_inputs/synthcity > results/x86/$*/log
	$(MAKE) copy_ref_tag-x86/$*

results/x86/current/log: build/x86/sfm
	$(MAKE) gen_results_dir_x86-current

results/x86/%/log: src/.git/refs/tags/%
	$(MAKE) checkout_goto-$*
	$(MAKE) gen_results_dir_x86-$*
	$(MAKE) checkout_return

results/x86/%/viso_cloud.ply: results/x86/%/log
	@[ -f $@ ]

#arm
gen_results_dir_arm-%: $(addprefix soc.mnt/results/,viso_cloud.ply log)
	@mkdir -p results/arm/$*
	cp $(addprefix soc.mnt/results/,viso_cloud.ply log) results/arm/$*/
	$(MAKE) copy_ref_tag-arm/$*
	$(MAKE) gen_aoc_symlink-$*

gen_aoc_symlink-%:
	[ -n "`ls -A src/viso/kernels`" ] && ln -sfT $$(relpath build/arm/aoc_cache/$$(cat build/arm/aoc_workspace/cl_hash) results/arm/$*) results/arm/$*/aoc || rm -f results/arm/$*/aoc

results/arm/current/log: $(addprefix soc.mnt/results/,viso_cloud.ply log)
	$(MAKE) gen_results_dir_arm-current

results/arm/%/log: src/.git/refs/tags/%
	$(MAKE) checkout_goto-$*
	$(MAKE) gen_results_dir_arm-$*
	$(MAKE) checkout_return

results/arm/%/viso_cloud.ply: results/arm/%/log
	@[ -f $@ ]

#quality plot
results/%/viso_cloud_C2M_DIST.asc: results/%/viso_cloud.ply
	CloudCompare -SILENT -NO_TIMESTAMP -C_EXPORT_FMT ASC -o $< -o video_inputs/synthcity/synthcity_mesh.ply -c2m_dist

results/%/viso_cloud_C2C_DIST.asc: results/%/viso_cloud.ply $(foreach i,i0 r29,results/x86/$(i)/viso_cloud.ply)
	CloudCompare -SILENT -NO_TIMESTAMP -C_EXPORT_FMT ASC -o $< -o results/x86/$$([ -f results/$*/ref_tag ] && cat results/$*/ref_tag || echo i0)/viso_cloud.ply -c2c_dist

$(addprefix results/%/,cloud.png error_hist.png error_cloud.png cloudref_error_hist.png cloudref_error_cloud.png): results/%/viso_cloud_C2M_DIST.asc results/%/viso_cloud_C2C_DIST.asc scripts/plot_clouds.py
	scripts/plot_clouds.py results/$*/viso_cloud_C2M_DIST.asc results/$*/viso_cloud_C2C_DIST.asc

#speed plot

define foreach_platform

$(eval plat = $(1))

list_impls_$(plat):
	@echo $$(sfm_impls_$(plat))

results/$(plat)/fps.png: $$(foreach i,$$(sfm_impls_$(plat)),results/$(plat)/$$(i)/log) $$(foreach i,$$(sfm_impls_$(plat)),results/$(plat)/$$(i)/error_hist.png) scripts/plot_fps.py
	for pattern in $(time_patterns); do; scripts/plot_fps.py src results $(plat) $$$$pattern; done

copy_ref_tag-$(plat)/%:
	[ -f src/ref_tag ] && cp src/ref_tag results/$(plat)/$$*/ || rm -f results/$(plat)/$$*/ref_tag
	
endef
$(foreach p,arm x86,$(eval $(call foreach_platform,$(p))))

results/fps.png: results/arm/fps.png results/x86/fps.png scripts/plot_fps.py
	for pattern in $(time_patterns); do; scripts/plot_fps.py src results both $$pattern; done

#soc mounts
soc.mnt/.mounted:
	sshfs -p 4007 root@$(soc_host):/home/dphoyes/FYP soc.mnt -o nonempty

soc.mnt/.unmounted:
	fusermount -u soc.mnt

soc.mnt/bin/%: build/arm/% soc.mnt/.mounted
	chrpath -r /home/dphoyes/lib $< >/dev/null
	rm -f $@
	cp $< $@
	touch $@

soc.mnt/results/log: soc.mnt/bin/sfm
	ssh -p 4007 root@$(soc_host) "cd ~dphoyes/FYP && bin/sfm $(sfm_params) -o results/viso_cloud.ply video_inputs/synthcity > results/log"
	touch $@

watch-arm: soc.mnt/bin/sfm
	ssh -p 4007 root@$(soc_host) "cd ~dphoyes/FYP && bin/sfm $(sfm_params) -o results/viso_cloud.ply video_inputs/synthcity"

soc.mnt/results/viso_cloud.ply: soc.mnt/results/log
	touch $@


clean:
	rm -r build

.SECONDARY:
