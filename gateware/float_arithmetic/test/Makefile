HDLDIR = ../../../
PYTHON = python3

CMD = PYTHONPATH=$(HDLDIR) $(PYTHON)

mult_tb:
	$(CMD) floatmult_tb.py

add_tb:
	$(CMD) floatadd_tb.py

clean:
	rm -rf *_*.png *.vvp *.v *.vcd

.PHONY: clean